# Traefik Starter Kit (Ansible & Docker)

A modular, production-ready Traefik v3 starter kit for turning your server into a container lab. It acts as the gateway/reverse proxy for all your containerized services (blogs, VPNs, dev tools, and web apps) with automated Let's Encrypt SSL/TLS.

## Features

- **Traefik v3**: Modern, fast reverse proxy.
- **Automated Wildcard Subdomain TLS**: Seamless Let's Encrypt certificates for any subdomain under your base domain via Cloudflare DNS + HTTP-01 challenge.
- **Dynamic SSH Inventory**: Automatically targets hosts from your local `~/.ssh/config`.
- **Pure Docker-Label Driven**: Zero config changes to Traefik when adding new services.
- **Traefik Dashboard**: Secure HTTPS web dashboard protected with HTTP Basic Authentication (`htpasswd`).
- **Instant Verification**: Includes a built-in lightweight `whoami` container to verify certificates and routing immediately.
- **Extensible Lab Network**: Dedicated external Docker bridge network (`traefik-public`) ready for any future container.

---

## Directory Structure

```text
├── ansible.cfg                          # Configured for dynamic ~/.ssh/config inventory
├── ssh_inventory.py                     # Dynamic inventory parsing local ~/.ssh/config
├── inventory/
│   ├── hosts.ini                        # Fallback static inventory
│   └── group_vars/
│       └── all.yml                      # Central configuration variables
├── playbook.yml                         # Main deployment playbook
├── roles/
│   └── traefik/                         # Core Traefik deployment role
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

---

## Quickstart

### 1. Configure Variables
Edit `inventory/group_vars/all.yml` with your domain and desired credentials:

```yaml
traefik_base_domain: "yourdomain.com"
traefik_acme_email: "admin@yourdomain.com"

traefik_dashboard_subdomain: "traefik"      # Accessible at traefik.yourdomain.com
traefik_dashboard_user: "admin"
traefik_dashboard_password: "YourSecretPassword!"

traefik_deploy_whoami: true
traefik_whoami_subdomain: "whoami"          # Accessible at whoami.yourdomain.com
```

### 2. Deploy to Your Server
Run the playbook targeting your SSH host:

```bash
ansible-playbook -l myserver playbook.yml
```

*(Or target a static host using `-i inventory/hosts.ini`)*.

### 3. Verify Deployment
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
