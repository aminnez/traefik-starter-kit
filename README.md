# Traefik Starter Kit (Ansible & Docker)

A modular, production-ready Traefik v3 starter kit for turning your server into a container lab. It acts as the gateway/reverse proxy for all your containerized services (blogs, VPNs, dev tools, and web apps) with automated Let's Encrypt SSL/TLS.

## Features

- **Traefik v3**: Modern, fast reverse proxy.
- **Automated Wildcard Subdomain TLS**: Seamless Let's Encrypt certificates for any subdomain under your base domain via Cloudflare DNS + HTTP-01 challenge.
- **Dynamic SSH Inventory**: Automatically targets hosts from your local `~/.ssh/config`.
- **Pure Docker-Label Driven**: Zero config changes to Traefik when adding new services.
- **Traefik Dashboard**: Secure HTTPS web dashboard protected with HTTP Basic Authentication (`htpasswd`).
- **Instant Verification**: Includes a built-in lightweight `whoami` container to verify certificates and routing immediately.
- **Scale-to-Zero on Demand**: Integrated Sablier daemon & Traefik plugin. Automatically stops idle containers and boots them back up on incoming HTTP requests.
- **Extensible Lab Network**: Dedicated external Docker bridge network (`traefik-public`) ready for any future container.

---

## Directory Structure

```text
├── .env.example                         # Example environment file template
├── ansible.cfg                          # Configured for dynamic ~/.ssh/config inventory
├── ssh_inventory.py                     # Dynamic inventory parsing local ~/.ssh/config
├── inventory/
│   ├── hosts.ini                        # Fallback static inventory
│   └── group_vars/
│       ├── all.yml                      # Dynamic variable resolution (Vault / .env / shell)
│       └── vault.yml                    # (Optional) Encrypted secrets via Ansible Vault
├── playbook.yml                         # Main deployment playbook
├── roles/
│   └── traefik/                         # Core Traefik deployment role
│       ├── defaults/main.yml            # Default infrastructure & service variables
│       └── tasks/main.yml               # Validation & provisioning tasks
└── examples/
    ├── hello-service/                   # Minimal example container stack
    └── README.md                        # Guide for adding new containers to the lab
```

---

## Prerequisites

1. **Remote Server**:
   - Ubuntu/Debian or Linux server with Docker and Docker Compose installed.
   - Ports `80` and `443` open in your firewall.
2. **DNS Record (Cloudflare)**:
   - A wildcard `A` record pointing to your server's public IP:
     - `*.yourdomain.com` -> `YOUR_SERVER_IP`
     - `yourdomain.com` -> `YOUR_SERVER_IP`
3. **SSH Access**:
   - An entry for your server in your local `~/.ssh/config`:
     ```ssh
     Host myserver
         HostName 203.0.113.10
         User root
         IdentityFile ~/.ssh/id_ed25519
     ```
4. **Local Control Machine**:
   - Python 3.10+ installed.

---

## Quickstart

### 1. Set Up Python Virtual Environment (Recommended)

To avoid PEP 668 package conflicts on modern Linux systems, use a dedicated virtual environment for Ansible and required dependencies (e.g. `passlib` and `bcrypt` for blowfish/bcrypt password hashing):

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Ansible and dependencies
pip install --upgrade pip
pip install ansible passlib
```

### 2. Configure Variables

Variables are dynamically resolved from **Ansible Vault**, an **Environment file (`.env`)**, or **Shell/CI Environment variables**. All infrastructure defaults (such as `/opt/traefik`, `traefik-public` network, and container image tags) are pre-configured in `roles/traefik/defaults/main.yml`.

Choose whichever configuration method fits your workflow:

#### Option A: Using an Environment File (`.env`) or Environment Variables (Simplest / CI-Friendly)

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and configure your domain, email, and password:
   ```ini
   TRAEFIK_BASE_DOMAIN=yourdomain.com
   TRAEFIK_ACME_EMAIL=admin@yourdomain.com
   TRAEFIK_DASHBOARD_USER=admin
   TRAEFIK_DASHBOARD_PASSWORD=YourStrongPasswordHere!
   ```

   *(Alternatively, export them directly in your shell or CI/CD environment without a file: `export TRAEFIK_BASE_DOMAIN=yourdomain.com`, etc.)*

3. Deploy:
   ```bash
   ansible-playbook -l myserver playbook.yml
   ```

---

#### Option B: Using Ansible Vault (Encrypted & Team-Friendly)

If you prefer encrypting secrets in Git or sharing encrypted credentials across a team:

1. Create an encrypted `vault.yml` (in the project root or in `inventory/group_vars/vault.yml`):
   ```bash
   ansible-vault create vault.yml
   ```
   *(Enter a master password when prompted).*

2. Add your required variables into `vault.yml`:
   ```yaml
   ---
   traefik_base_domain: "yourdomain.com"
   traefik_acme_email: "admin@yourdomain.com"
   traefik_dashboard_user: "admin"
   traefik_dashboard_password: "YourStrongPasswordHere!"
   ```
   *(You can also use prefixed variables like `vault_traefik_dashboard_password`)*.

3. Deploy by passing the vault password:
   ```bash
   ansible-playbook -l myserver playbook.yml --ask-vault-pass
   ```

   **Tip (Password File)**: To avoid typing the vault password on every run:
   ```bash
   echo "your-vault-password" > .vault_password
   chmod 600 .vault_password
   ```
   Uncomment `# vault_password_file = .vault_password` in `ansible.cfg`, and then simply run:
   ```bash
   ansible-playbook -l myserver playbook.yml
   ```

---

### 3. Deploy to Your Server
Run the playbook targeting your SSH host:

```bash
# When using .env or shell environment variables:
ansible-playbook -l myserver playbook.yml

# When using Ansible Vault:
ansible-playbook -l myserver playbook.yml --ask-vault-pass
```

*(Or target a static host using `-i inventory/hosts.ini`)*.

### 4. Verify Deployment
Once the playbook completes:
- **Test Routing & SSL**: Visit `https://whoami.yourdomain.com` in your browser. You should see a valid Let's Encrypt certificate and request headers.
- **Access Dashboard**: Visit `https://traefik.yourdomain.com` and log in with your configured username and password.

---

## Adding New Lab Containers

To add a new service (e.g. Ghost, Nextcloud, WireGuard UI), simply attach it to `traefik-public` and add Traefik labels in its `docker-compose.yml`:

```yaml
services:
  myapp:
    image: myapp:latest
    networks:
      - traefik-public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`myapp.yourdomain.com`)"
      - "traefik.http.routers.myapp.entrypoints=websecure"
      - "traefik.http.routers.myapp.tls=true"
      - "traefik.http.routers.myapp.tls.certresolver=myresolver"
      - "traefik.http.services.myapp.loadbalancer.server.port=8080"

networks:
  traefik-public:
    external: true
```

See [examples/README.md](examples/README.md) for full details and recipes.

---

## Scale-to-Zero on Demand (Sablier)

This kit integrates [Sablier](https://github.com/sablierapp/sablier) and the [Sablier Traefik Plugin](https://github.com/sablierapp/sablier-traefik-plugin) to save CPU and RAM on resource-constrained servers.

- **How it works**: Containers configured for Sablier are automatically shut down when idle. When an incoming request reaches Traefik, the Sablier plugin intercepts the traffic, displays an animated waiting screen (theme: `hacker-terminal`), signals Docker to wake up the container, and forwards the request transparently once the service is ready.
- **Shared Gateway Endpoint**: The Sablier daemon runs on the `traefik-public` network at `http://sablier:10000`, allowing any container in your lab to scale to zero on demand.

### Sablier Role Configuration (`roles/traefik/defaults/main.yml`)

| Variable | Default | Description |
|---|---|---|
| `traefik_sablier_enabled` | `true` | Enable/disable the Sablier daemon and Traefik plugin |
| `traefik_sablier_image` | `sablierapp/sablier:latest` | Docker image for Sablier daemon |
| `traefik_sablier_plugin_version` | `v1.3.1` | Version of the Traefik Sablier plugin |
| `traefik_sablier_url` | `http://sablier:10000` | Generic internal URL for Sablier API |
| `traefik_sablier_default_session_duration` | `5m` | Default idle timeout before containers stop |
| `traefik_sablier_default_theme` | `hacker-terminal` | Default waiting page theme (`ghost`, `matrix`, `classic`, etc.) |
| `traefik_whoami_sablier_enabled` | `true` | Enable scale-to-zero specifically for the built-in `whoami` sample |
| `traefik_whoami_sablier_group` | `whoami` | Sablier group name for `whoami` |
| `traefik_whoami_sablier_session_duration` | `5m` | Session timeout for `whoami` |

For instructions on configuring custom containers to scale to zero, see [examples/README.md](examples/README.md#scale-to-zero-on-demand-sablier).
