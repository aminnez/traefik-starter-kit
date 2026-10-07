# Traefik Server Starter Kit Specification

- **Date**: 2026-10-07
- **Project**: `traefik-setup-ansible`
- **Status**: Draft for Review

---

## 1. Overview & Objective

The goal of this project is to build an initial, clean, and extensible Traefik starter kit for a server that serves as a container lab. It acts as the gateway/reverse-proxy base for all present and future containerized services (such as blogs, VPNs, web apps, monitoring, and developer tools) while keeping configuration minimal, robust, and reproducible.

### Key Goals
1. **Container Lab Gateway**: Dedicated external Docker network (`traefik-public`) allowing any future container on the server to automatically register routing and SSL certificates simply by attaching to the network and specifying Docker labels.
2. **Automated SSL/TLS with Let's Encrypt**: Support for wildcard subdomains pointed to the server via Cloudflare DNS using automated Let's Encrypt HTTP-01 challenges on port 80/443.
3. **Ansible Automation & SSH Config**: Automated deployment using an Ansible role, mirroring the user's environment SSH configuration (`enable_ssh_config = True`, `inventory = ./ssh_inventory.py`) so any host defined in `~/.ssh/config` can be targeted directly.
4. **Pure Docker-Label Driven**: No dynamic file provider needed—all routers, services, entrypoints, and middlewares (including Traefik Dashboard basic authentication) are declared through Docker labels.
5. **Lightweight Verification Service**: Includes an ultra-lightweight `whoami` service to test DNS, certificate generation, routing, and HTTP-to-HTTPS redirection immediately.
6. **Starter Container Example**: Includes a lightweight example in `examples/hello-service` demonstrating how to connect new services into the lab.

---

## 2. Architecture & Directory Layout

### 2.1 Repository Structure
```text
traefik-setup-ansible/
├── ansible.cfg                          # Ansible configuration referencing dynamic SSH inventory
├── ssh_inventory.py                     # Dynamic inventory parsing local ~/.ssh/config
├── inventory/
│   ├── hosts.ini                        # Fallback static inventory
│   └── group_vars/
│       └── all.yml                      # Central variables (domains, email, dashboard credentials)
├── playbook.yml                         # Main deployment playbook applying the traefik role
├── roles/
│   └── traefik/
│       ├── defaults/main.yml            # Default configuration variables
│       ├── tasks/main.yml               # Idempotent provisioning tasks
│       ├── handlers/main.yml            # Container restart handlers on config change
│       └── templates/
│           ├── docker-compose.yml.j2    # Traefik stack and sample whoami container
│           └── traefik.yml.j2           # Traefik static configuration
├── examples/
│   ├── hello-service/
│   │   └── docker-compose.yml           # Minimal standalone compose file demonstrating lab attachment
│   └── README.md                        # Documentation on how to deploy new lab services
└── README.md                            # Project overview and quickstart instructions
```

### 2.2 Server Runtime Layout (`/opt/traefik`)
On the target server, files are placed under `/opt/traefik`:
* `/opt/traefik/docker-compose.yml`: Live stack definition.
* `/opt/traefik/traefik.yml`: Static configuration loaded at Traefik startup.
* `/opt/traefik/acme/acme.json`: Certificate store created with strict `0600` permissions.
* `/opt/traefik/logs/`: Optional directory for Traefik log files.

---

## 3. SSH Configuration & Inventory

Following the user's existing environment pattern (`/home/amin/Documents/projects/ansible-molecule-oh-my-zsh-example/ansible.cfg`):

### 3.1 `ansible.cfg`
```ini
[defaults]
bin_ansible_callbacks = True
interpreter_python = auto_silent
enable_ssh_config = True
inventory = ./ssh_inventory.py

[ssh_connection]
ssh_args = -C -o ControlMaster=auto -o ControlPersist=60s
pipelining = True
```

### 3.2 `ssh_inventory.py`
A Python script that reads `~/.ssh/config` and returns Ansible-compatible JSON inventory containing:
* `ansible_host`: HostName from ssh config
* `ansible_port`: Port from ssh config (default 22)
* `ansible_user`: User from ssh config
* `ansible_ssh_private_key_file`: IdentityFile from ssh config
* `ansible_ssh_common_args`: ProxyCommand or custom SSH arguments

---

## 4. Traefik Static Configuration (`traefik.yml.j2`)

```yaml
api:
  dashboard: true
  insecure: false

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    watch: true
    exposedByDefault: false
    network: "{{ traefik_network_name }}"

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true

  websecure:
    address: ":443"
    http:
      tls:
        certResolver: myresolver

certificatesResolvers:
  myresolver:
    acme:
      email: "{{ traefik_acme_email }}"
      storage: "/etc/traefik/acme/acme.json"
      httpChallenge:
        entryPoint: web

log:
  level: "{{ traefik_log_level | default('INFO') }}"
```

---

## 5. Traefik Docker Compose Stack (`docker-compose.yml.j2`)

The stack runs Traefik v3 and the verification `whoami` service.

```yaml
services:
  traefik:
    image: "traefik:{{ traefik_image_tag | default('v3.1') }}"
    container_name: traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - {{ traefik_install_dir }}/traefik.yml:/etc/traefik/traefik.yml:ro
      - {{ traefik_install_dir }}/acme:/etc/traefik/acme:rw
    networks:
      - {{ traefik_network_name }}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`{{ traefik_dashboard_subdomain }}.{{ traefik_base_domain }}`)"
      - "traefik.http.routers.dashboard.service=api@internal"
      - "traefik.http.routers.dashboard.entrypoints=websecure"
      - "traefik.http.routers.dashboard.tls=true"
      - "traefik.http.routers.dashboard.tls.certresolver=myresolver"
      - "traefik.http.routers.dashboard.middlewares=dash-auth"
      - "traefik.http.middlewares.dash-auth.basicauth.users={{ traefik_dashboard_user }}:{{ traefik_dashboard_auth_hash }}"

{% if traefik_deploy_whoami | default(true) %}
  whoami:
    image: traefik/whoami:latest
    container_name: traefik-whoami
    restart: unless-stopped
    networks:
      - {{ traefik_network_name }}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.whoami.rule=Host(`{{ traefik_whoami_subdomain }}.{{ traefik_base_domain }}`)"
      - "traefik.http.routers.whoami.entrypoints=websecure"
      - "traefik.http.routers.whoami.tls=true"
      - "traefik.http.routers.whoami.tls.certresolver=myresolver"
      - "traefik.http.services.whoami.loadbalancer.server.port=80"
{% endif %}

networks:
  {{ traefik_network_name }}:
    external: true
```

---

## 6. Variables Schema (`group_vars/all.yml` & `roles/traefik/defaults/main.yml`)

```yaml
# Server Base Domain & Let's Encrypt
traefik_base_domain: "example.com"
traefik_acme_email: "admin@example.com"

# Traefik Dashboard Credentials
traefik_dashboard_subdomain: "traefik"
traefik_dashboard_user: "admin"
traefik_dashboard_password: "ChangeMeInVault!"

# Internal hashing helper in Ansible:
# traefik_dashboard_auth_hash is generated dynamically via password_hash('apr1_crypt')

# Infrastructure & Directories
traefik_install_dir: "/opt/traefik"
traefik_network_name: "traefik-public"
traefik_image_tag: "v3.1"
traefik_log_level: "INFO"

# Built-in Verification Service
traefik_deploy_whoami: true
traefik_whoami_subdomain: "whoami"
```

---

## 7. Ansible Role Tasks (`roles/traefik/tasks/main.yml`)

1. **Prerequisites check**: Validates Docker daemon is running and python docker library/compose plugin is available.
2. **Docker Network**: Ensures `traefik-public` exists using `community.docker.docker_network`.
3. **Directories**: Creates `{{ traefik_install_dir }}` and `{{ traefik_install_dir }}/acme` with `0755` permissions.
4. **ACME Storage**: Creates `{{ traefik_install_dir }}/acme/acme.json` with strict `0600` permissions if it does not exist.
5. **Generate Credentials Hash**: Uses Ansible's `password_hash('apr1_crypt')` to hash `traefik_dashboard_password` for htpasswd format.
6. **Templates**:
   - Deploys `traefik.yml` to `{{ traefik_install_dir }}/traefik.yml`.
   - Deploys `docker-compose.yml` to `{{ traefik_install_dir }}/docker-compose.yml`.
7. **Deploy Stack**: Deploys the stack using `community.docker.docker_compose_v2` (with automated fallback to command execution `docker compose up -d`).

---

## 8. Universal Workflow for Adding Lab Containers

Any future lab container (e.g. blog, VPN, developer tools) requires no changes to Traefik:

### Step 1: Create a service folder on the server (e.g., `/opt/my-lab-app/docker-compose.yml`)
### Step 2: Write compose definition:
```yaml
services:
  app:
    image: my-service:latest
    restart: unless-stopped
    networks:
      - traefik-public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`myapp.example.com`)"
      - "traefik.http.routers.myapp.entrypoints=websecure"
      - "traefik.http.routers.myapp.tls=true"
      - "traefik.http.routers.myapp.tls.certresolver=myresolver"
      - "traefik.http.services.myapp.loadbalancer.server.port=8080"

networks:
  traefik-public:
    external: true
```
### Step 3: Start the service:
```bash
docker compose up -d
```
Traefik immediately routes traffic for `https://myapp.example.com` to the container and provisions a Let's Encrypt certificate.

---

## 9. Verification & Testing Plan

1. **Syntax & Linter**: Validate Ansible files with `ansible-playbook --syntax-check` and YAML linter.
2. **Local Validation**: Test `ssh_inventory.py` execution against local environment.
3. **Template Rendering**: Verify Jinja2 templating syntax for `traefik.yml.j2` and `docker-compose.yml.j2`.
4. **Live Verification (on deployment)**:
   - Check `curl -I http://whoami.domain.com` returns 301/308 redirect to HTTPS.
   - Check `curl -I https://whoami.domain.com` returns 200 OK with valid Let's Encrypt TLS certificate.
   - Check `curl -I https://traefik.domain.com` returns 401 Unauthorized without auth, and 200 OK with `admin:password`.
