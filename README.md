# Traefik Starter Kit (Ansible & Docker)

A modular, production-ready Traefik v3 starter kit for turning your server into a container lab. It acts as the gateway/reverse proxy for all your containerized services (blogs, VPNs, dev tools, and web apps) with automated Let's Encrypt SSL/TLS.

## Features

- **Traefik v3**: Modern, fast reverse proxy.
- **Dynamic File Provider & Minimal Labels**: Dynamic configuration via `/etc/traefik/dynamic/`. Downstream containers only need 2–3 labels.
- **ACME DNS-01 & HTTP-01 Challenges**: Automated wildcard certificates (`*.yourdomain.com`) using Cloudflare API tokens or HTTP-01 challenge.
- **Optional Docker Socket Proxy**: Hardened isolation using `tecnativa/docker-socket-proxy` to prevent direct root Docker socket exposure.
- **Built-in Security Headers**: Out-of-the-box HSTS, FrameDeny, Nosniff, and strict CSP policies applied automatically.
- **Observability**: Structured JSON access logging, Prometheus metrics endpoint, and automated post-deployment URI health checks.
- **Certificate Backup & Restore**: Standalone `backup_acme.yml` playbook for secure `acme.json` backups (mode 0600) and restoration.
- **Dynamic SSH Inventory**: Automatically targets hosts from your local `~/.ssh/config`.
- **Traefik Dashboard**: Secure HTTPS web dashboard protected with HTTP Basic Authentication (`htpasswd`).
- **Instant Verification**: Includes a built-in lightweight `whoami` container to verify certificates and routing immediately.
- **Scale-to-Zero on Demand**: Integrated Sablier daemon & Traefik plugin. Automatically stops idle containers and boots them back up on incoming HTTP requests.
- **Extensible Lab Network**: Dedicated external Docker bridge network (`traefik-public`) ready for any future container.
- **Automated CI/CD**: Full GitHub Actions test suite and syntax validation pipeline.

---

## Directory Structure

```text
├── .github/workflows/ci.yml             # Automated CI pipeline
├── .env.example                         # Example environment file template
├── ansible.cfg                          # Configured for dynamic ~/.ssh/config inventory
├── backup_acme.yml                      # Certificate backup and restore playbook
├── requirements.txt                     # Pinned Python dependencies
├── requirements.yml                     # Ansible Galaxy collection dependencies
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
│       ├── tasks/main.yml               # Validation & provisioning tasks
│       └── templates/                   # Static, compose & dynamic templates
└── examples/
    ├── hello-service/                   # Minimal example container stack
    └── README.md                        # Guide for adding new containers to the lab
```

---

## Prerequisites

1. **Remote Server**:
   - Ubuntu/Debian or Linux server with Docker and Docker Compose installed.
   - Ports `80` and `443` open in your firewall.
2. **DNS Record**:
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

### 1. Set Up Python Virtual Environment & Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Ansible, Pytest, and Galaxy collections
pip install --upgrade pip
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
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

Thanks to Traefik v3 entrypoint defaults and the dynamic configuration provider, adding a new service only requires **3 labels**:

```yaml
services:
  myapp:
    image: myapp:latest
    networks:
      - traefik-public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`myapp.yourdomain.com`)"
      - "traefik.http.services.myapp.loadbalancer.server.port=8080"

networks:
  traefik-public:
    external: true
```

*(TLS, certificate resolver, and security headers are handled automatically by Traefik's `websecure` entrypoint).*

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

---

## ACME DNS-01 Challenge & Wildcards

By default, Traefik uses the `http` challenge (port 80). If you want **wildcard certificates** (`*.yourdomain.com`) or your server is behind a NAT/firewall without port 80 exposed, switch to the `dns` challenge:

In `.env`:
```ini
TRAEFIK_ACME_CHALLENGE_TYPE=dns
CF_DNS_API_TOKEN=your_cloudflare_api_token_here
TRAEFIK_ACME_WILDCARD_ENABLED=true
```

| Variable | Default | Description |
|---|---|---|
| `traefik_acme_challenge_type` | `http` | Challenge type: `http` or `dns` |
| `traefik_acme_dns_provider` | `cloudflare` | DNS provider name for lego/Traefik |
| `traefik_acme_dns_resolvers` | `['1.1.1.1:53', '8.8.8.8:53']` | Recursive DNS resolvers for challenge validation |
| `traefik_acme_wildcard_enabled` | `false` | Automatically configure wildcard TLS domains |

---

## Built-in Security Hardening (Secure by Default)

### 1. Docker Socket Proxy
Exposing the raw `/var/run/docker.sock` to Traefik gives it container root privileges. This starter kit isolates Traefik **by default** using a dedicated read-only socket proxy container (`tecnativa/docker-socket-proxy`):

- **Enabled by default**: `traefik_socket_proxy_enabled: true`
- Traefik mounts no host sockets and accesses Docker read-only over `tcp://docker-proxy:2375`.
- To disable and mount the Docker socket directly: set `traefik_socket_proxy_enabled: false`.

### 2. Preconfigured Security Headers & Rate Limiting
Preconfigured dynamic middlewares in `/etc/traefik/dynamic/middlewares.yml`:
- **Security Headers (`sec-headers@file`)**: Enabled by default (`traefik_security_headers_enabled: true`). Enforces HSTS (1 year, preload), `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, and strict referrer policy.
- **Rate Limiting (`rate-limit@file`)**: Enabled by default (`traefik_ratelimit_enabled: true`) with configurable average (default `100` req/s) and burst (default `50`). Attach to any router using `- "traefik.http.routers.myapp.middlewares=rate-limit@file"`.

---

## Observability & Operations

### JSON Access Logs & Prometheus Metrics
- **JSON Access Logs**: Enabled by default (`traefik_access_log_enabled: true`) emitting structured JSON access logs to Docker stdout for easy debugging and Fail2ban/CrowdSec parsing.
- **Prometheus Metrics**: Optional (`traefik_metrics_prometheus_enabled: true`) exposing metrics on `:8080/metrics`.

### Health Check Verification
After deployment, Ansible automatically polls the Traefik HTTP endpoint using `ansible.builtin.uri` with retries to confirm the stack is healthy and serving traffic before completing.

---

## Certificate Backup & Restore

To protect your Let's Encrypt certificates from rate limits during server rebuilds, use the included [`backup_acme.yml`](backup_acme.yml) playbook:

```bash
# Backup acme.json to local backups/ folder (mode 0600):
ansible-playbook -l myserver backup_acme.yml

# Restore a saved backup onto the server:
ansible-playbook -l myserver backup_acme.yml -e "restore_file=backups/acme-myserver-20261008.json"
```

---

## Automated Validation & Testing

Run the full local test suite (template rendering, task verification, and syntax checks):

```bash
./tests/run_all_checks.sh
```
All commits are also continuously tested via GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

