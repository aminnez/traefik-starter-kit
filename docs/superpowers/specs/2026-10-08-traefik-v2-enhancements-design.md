# Traefik Starter Kit v2 Enhancements Specification

## 1. Overview & Objectives

This specification outlines the architecture and implementation for upgrading the Traefik Starter Kit with:
1. **Dynamic File Provider & Container Label Reduction**: Enable `/etc/traefik/dynamic/` file provider, remove dashboard labels completely from Docker Compose, and establish entrypoint-level middlewares so downstream lab containers only need 2-3 labels.
2. **ACME DNS-01 Challenge & Wildcard Certificates**: Support automated issuance for `*.domain.com` without requiring open port 80, featuring first-class Cloudflare API Token integration and extensible provider support.
3. **Optional Traefik-Level Security Hardening**: Provide an optional Docker Socket Proxy (`tecnativa/docker-socket-proxy`) to eliminate root Docker socket exposure, along with preconfigured security headers (HSTS, CSP, FrameDeny, Nosniff) and rate limiting.
4. **Observability & Operations**: Add configurable JSON access logging, Prometheus metrics endpoint, post-deployment Ansible URI health check verification, and an automated ACME certificate backup and restore playbook (`backup_acme.yml`).
5. **Repository & CI/CD Tooling**: Standardize dependencies via `requirements.txt` and `requirements.yml`, add an automated GitHub Actions CI pipeline, and expand the Pytest suite to validate all new configuration branches.

---

## 2. Architecture & File Layout

```
traefik-setup-ansible/
├── .github/
│   └── workflows/
│       └── ci.yml                          # Automated GitHub Actions test & syntax pipeline
├── roles/
│   └── traefik/
│       ├── defaults/
│       │   └── main.yml                    # Extended defaults with toggle flags
│       ├── handlers/
│       │   └── main.yml                    # Handlers (restart stack)
│       ├── tasks/
│       │   └── main.yml                    # Directory creation, template deployments, healthcheck
│       └── templates/
│           ├── traefik.yml.j2              # Static configuration (file provider, dnsChallenge, metrics)
│           ├── docker-compose.yml.j2       # Stack definition (socket proxy, env vars, clean labels)
│           └── dynamic/
│               ├── dashboard.yml.j2        # Dashboard router & basicauth middleware in YAML
│               └── middlewares.yml.j2      # Security headers & rate limit middlewares
├── inventory/
│   ├── group_vars/
│   │   └── all.yml                         # Dynamic resolution (Vault > .env > Env)
│   └── hosts.ini
├── tests/
│   ├── test_templates_rendering.py         # Expanded Jinja2 rendering test suite
│   ├── test_role_tasks.py                  # Task assertion checks
│   └── run_all_checks.sh                   # Local execution script
├── backup_acme.yml                         # ACME certificate backup & restore playbook
├── playbook.yml                            # Main deployment playbook
├── requirements.txt                        # Pinned Python dependencies for Ansible & Pytest
├── requirements.yml                        # Ansible Galaxy collections
├── .env.example                            # Sample environment variables including DNS tokens
└── README.md                               # Updated documentation
```

---

## 3. Detailed Component Specifications

### 3.1 Dynamic Configuration & Label Reduction
* **Runtime Directory**: `/opt/traefik/dynamic` created on remote host with permissions `0755` and mounted into the Traefik container as `/etc/traefik/dynamic:ro`.
* **File Provider in `traefik.yml.j2`**:
  ```yaml
  providers:
    docker:
      endpoint: "{{ 'tcp://docker-proxy:2375' if traefik_socket_proxy_enabled | default(false) else 'unix:///var/run/docker.sock' }}"
      watch: true
      exposedByDefault: false
      network: "{{ traefik_network_name }}"
    file:
      directory: "/etc/traefik/dynamic"
      watch: true
  ```
* **Dashboard Dynamic Template (`dynamic/dashboard.yml.j2`)**:
  Eliminates all labels from the Traefik service in `docker-compose.yml.j2`:
  ```yaml
  http:
    routers:
      dashboard:
        rule: "Host(`{{ traefik_dashboard_subdomain }}.{{ traefik_base_domain }}`)"
        service: "api@internal"
        entryPoints:
          - "websecure"
        middlewares:
          - "dash-auth"
    middlewares:
      dash-auth:
        basicAuth:
          users:
            - "{{ traefik_dashboard_user }}:{{ traefik_dashboard_auth_hash }}"
  ```
* **Entrypoint-Level Middlewares**:
  When `traefik_security_headers_enabled: true`, `sec-headers@file` is attached directly to `entryPoints.websecure.http.middlewares` in `traefik.yml.j2`. All downstream routers listening on `websecure` automatically receive security headers without specifying any labels.
* **Streamlined Container Labels**:
  Any Docker service container (e.g. `whoami` or `examples/hello-service`) now only requires:
  ```yaml
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.myapp.rule=Host(`myapp.example.com`)"
    - "traefik.http.services.myapp.loadbalancer.server.port=80"
  ```

---

### 3.2 ACME DNS-01 Challenge & Wildcards

#### Variables
* `traefik_acme_challenge_type`: `"http"` (default) or `"dns"`.
* `traefik_acme_dns_provider`: `"cloudflare"` (default for DNS challenge).
* `traefik_acme_dns_resolvers`: `["1.1.1.1:53", "8.8.8.8:53"]`.
* `traefik_acme_wildcard_enabled`: boolean (default `false`).
* `traefik_acme_dns_env_vars`: Dictionary of environment variables passed to the Traefik container.
  Default for Cloudflare:
  ```yaml
  CF_DNS_API_TOKEN: "{{ vault_cf_dns_api_token | default(lookup('ansible.builtin.ini', 'CF_DNS_API_TOKEN type=properties file=.env', errors='ignore', default=''), true) | default(lookup('ansible.builtin.env', 'CF_DNS_API_TOKEN', default=''), true) | trim }}"
  ```

#### Resolver in `traefik.yml.j2`
```yaml
certificatesResolvers:
  myresolver:
    acme:
      email: "{{ traefik_acme_email }}"
      storage: "/etc/traefik/acme/acme.json"
{% if traefik_acme_challenge_type | default('http') == 'dns' %}
      dnsChallenge:
        provider: "{{ traefik_acme_dns_provider | default('cloudflare') }}"
        resolvers:
{% for resolver in traefik_acme_dns_resolvers | default(['1.1.1.1:53', '8.8.8.8:53']) %}
          - "{{ resolver }}"
{% endfor %}
{% else %}
      httpChallenge:
        entryPoint: web
{% endif %}
```

#### Wildcard TLS Domains
When `traefik_acme_wildcard_enabled: true` and `traefik_acme_challenge_type == 'dns'`, configure default certificate domains on entrypoint `websecure`:
```yaml
    entryPoints:
      websecure:
        address: ":443"
        http:
          tls:
            certResolver: myresolver
            domains:
              - main: "{{ traefik_base_domain }}"
                sans:
                  - "*.{{ traefik_base_domain }}"
```

---

### 3.3 Optional Traefik-Level Security Hardening

#### Docker Socket Proxy
* `traefik_socket_proxy_enabled`: boolean (default `false`).
* When `false`: Traefik mounts `/var/run/docker.sock:/var/run/docker.sock:ro`.
* When `true`:
  * Traefik mounts no Docker socket.
  * `docker-proxy` service runs `tecnativa/docker-socket-proxy:latest` on `{{ traefik_network_name }}`:
    ```yaml
    docker-proxy:
      image: tecnativa/docker-socket-proxy:latest
      container_name: traefik-docker-proxy
      restart: unless-stopped
      environment:
        - CONTAINERS=1
        - SERVICES=1
        - NETWORKS=1
        - TASKS=1
        - POST=0
        - DELETE=0
        - PUT=0
      volumes:
        - /var/run/docker.sock:/var/run/docker.sock:ro
      networks:
        - {{ traefik_network_name }}
    ```
  * Traefik connects to `tcp://docker-proxy:2375`.

#### Dynamic Middlewares (`dynamic/middlewares.yml.j2`)
* `traefik_security_headers_enabled`: boolean (default `true`).
  Defines `sec-headers`:
  * `stsSeconds: 31536000`
  * `stsIncludeSubdomains: true`
  * `stsPreload: true`
  * `forceSTSHeader: true`
  * `contentTypeNosniff: true`
  * `browserXssFilter: true`
  * `frameDeny: true`
  * `referrerPolicy: "strict-origin-when-cross-origin"`
* `traefik_ratelimit_enabled`: boolean (default `false`).
  Defines `rate-limit`:
  * `average: "{{ traefik_ratelimit_average | default(100) }}"`
  * `burst: "{{ traefik_ratelimit_burst | default(50) }}"`

---

### 3.4 Observability & Operations

#### Logs & Metrics in `traefik.yml.j2`
* `traefik_access_log_enabled`: boolean (default `false`).
  ```yaml
  accessLog:
    format: json
    filePath: "/etc/traefik/access.log" # or stdout when empty
  ```
* `traefik_metrics_prometheus_enabled`: boolean (default `false`).
  ```yaml
  metrics:
    prometheus:
      addEntryPointsLabels: true
      addServicesLabels: true
  ```

#### Post-Deployment Healthcheck (`roles/traefik/tasks/main.yml`)
After `docker compose up -d`, poll the HTTP endpoint:
```yaml
- name: Wait for Traefik to respond on HTTP port
  ansible.builtin.uri:
    url: "http://127.0.0.1:80"
    status_code: [200, 301, 302, 404]
    follow_redirects: none
  register: traefik_health
  until: traefik_health.status in [200, 301, 302, 404]
  retries: 12
  delay: 2
```

#### ACME Certificate Backup Playbook (`backup_acme.yml`)
* Standalone playbook: `ansible-playbook backup_acme.yml`
* Fetches `/opt/traefik/acme/acme.json` from the target host to a local `backups/acme-{{ inventory_hostname }}-{{ timestamp }}.json` file with mode `0600`.
* Supports restore mode: `ansible-playbook backup_acme.yml -e "restore_file=backups/my-acme.json"`.

---

### 3.5 Repository & CI/CD Tooling

#### Dependencies (`requirements.txt` & `requirements.yml`)
* `requirements.txt`:
  ```txt
  ansible-core>=2.15.0,<2.19.0
  pytest>=8.0.0
  jinja2>=3.1.0
  pyyaml>=6.0
  ```
* `requirements.yml`:
  ```yaml
  ---
  collections:
    - name: community.docker
      version: ">=3.10.0"
  ```

#### GitHub Actions Workflow (`.github/workflows/ci.yml`)
Runs on push and pull_request:
1. Set up Python 3.11 / 3.12.
2. Install `requirements.txt` and `requirements.yml`.
3. Run `pytest tests/ -v`.
4. Validate Ansible playbook syntax:
   `ansible-playbook --syntax-check playbook.yml backup_acme.yml`.

---

## 4. Verification & Testing Strategy

1. **Jinja2 Rendering Unit Tests (`tests/test_templates_rendering.py`)**:
   * Test HTTP-01 challenge rendering (default).
   * Test DNS-01 challenge rendering with Cloudflare and custom resolvers.
   * Test Wildcard domain rendering.
   * Test Docker Socket Proxy enabled (tcp endpoint + proxy service) vs disabled (unix socket mount).
   * Test Dynamic templates: `dashboard.yml` and `middlewares.yml` (security headers & rate limit).
   * Test Observability: Prometheus metrics and JSON access logs enabled vs disabled.
2. **Playbook Syntax & Task Assertions**:
   * Verify all tasks compile and syntax-check cleanly with `ansible-playbook --syntax-check`.
   * Verify `tests/run_all_checks.sh` passes 100%.

---

## 5. Spec Self-Review Checklist

* **Placeholder Scan**: No `TODO`, `TBD`, or unconfigured values; all defaults specified with fallbacks.
* **Internal Consistency**: Variables defined in `group_vars/all.yml` match `defaults/main.yml`, templates, and tests.
* **Scope Check**: Fits cleanly within the Traefik stack without touching host firewalls (UFW) or Fail2ban.
* **Ambiguity Check**: Backward compatibility preserved (`httpChallenge` remains default; socket proxy remains opt-in).
