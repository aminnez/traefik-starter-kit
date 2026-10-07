# Traefik Starter Kit v2 Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement v2 enhancements for Traefik Starter Kit including dynamic file provider configuration, container label reduction, ACME DNS-01 & wildcard certificates, optional Docker socket proxy & security middlewares, observability & operational playbooks, and repository CI/CD tooling.

**Architecture:** Maintain a clean, backward-compatible Ansible role structure. Mount `/opt/traefik/dynamic` into Traefik to decouple middlewares and routers from container labels. Support both HTTP and DNS ACME challenge types, optional socket isolation via `tecnativa/docker-socket-proxy`, Prometheus metrics/JSON access logs, and automated testing with GitHub Actions.

**Tech Stack:** Ansible Core, Docker & Docker Compose, Traefik v3, Jinja2, Pytest, Python 3.

**Spec:** [`docs/superpowers/specs/2026-10-08-traefik-v2-enhancements-design.md`](file:///home/amin/Documents/projects2/traefik-setup-ansible/docs/superpowers/specs/2026-10-08-traefik-v2-enhancements-design.md)

## Global Constraints

- Python dependencies pinned in `requirements.txt` (`ansible-core>=2.15.0`, `pytest>=8.0.0`, `jinja2>=3.1.0`, `pyyaml>=6.0`).
- Ansible Galaxy collections listed in `requirements.yml` (`community.docker>=3.10.0`).
- Default challenge type is `http` (`traefik_acme_challenge_type: "http"`) preserving existing behavior.
- Docker Socket Proxy is disabled by default (`traefik_socket_proxy_enabled: false`).
- All changes must pass `pytest tests/ -v` and syntax check `./tests/test_playbook_syntax.sh`.

## Review Focus

1. **DNS-01 API Token validation**: If `traefik_acme_challenge_type == 'dns'` and provider is `cloudflare`, verify `CF_DNS_API_TOKEN` is supplied; fail early if missing.
2. **Dynamic directory creation**: Ensure `/opt/traefik/dynamic` exists with `0755` permissions prior to template deployment.
3. **Socket proxy network isolation**: Ensure `docker-proxy` container only exposes port 2375 to `traefik-public` network without publishing it to host ports.
4. **Health check termination**: Ensure `ansible.builtin.uri` polling uses bounded retries (`retries: 12`, `delay: 2`) so it does not hang indefinitely if startup fails.
5. **ACME backup confidentiality**: Ensure `backup_acme.yml` creates destination backup files with strict `0600` permissions.

---

### Task 1: Repository Tooling & CI Pipeline

**Files:**
- Create: `requirements.txt`
- Create: `requirements.yml`
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: Existing pytest test suite and playbook syntax scripts.
- Produces: Standardized python/ansible environment and automated GitHub Actions verification.

- [ ] **Step 1: Create requirements.txt and requirements.yml**
Create `requirements.txt` pinning `ansible-core>=2.15.0,<2.19.0`, `pytest>=8.0.0`, `jinja2>=3.1.0`, `pyyaml>=6.0`.
Create `requirements.yml` with `community.docker>=3.10.0`.

- [ ] **Step 2: Create GitHub Actions workflow `.github/workflows/ci.yml`**
Trigger on `push` and `pull_request` on all branches.
Steps: Checkout repo, Set up Python 3.12, Install `requirements.txt` and `ansible-galaxy install -r requirements.yml`, Run `pytest tests/ -v`, Run `./tests/test_playbook_syntax.sh`.

- [ ] **Step 3: Verify local dependency consistency and tests**
Run: `pytest tests/ -v`
Expected: 9 passed in < 1s.

- [ ] **Step 4: Commit**
```bash
git add requirements.txt requirements.yml .github/workflows/ci.yml
git commit -m "ci: add requirements manifests and github actions workflow"
```

---

### Task 2: Dynamic File Provider & Traefik Dashboard Label Elimination

**Files:**
- Create: `roles/traefik/templates/dynamic/dashboard.yml.j2`
- Modify: `roles/traefik/templates/traefik.yml.j2`
- Modify: `roles/traefik/templates/docker-compose.yml.j2`
- Modify: `roles/traefik/tasks/main.yml`
- Test: `tests/test_templates_rendering.py`

**Interfaces:**
- Consumes: `traefik_install_dir`, `traefik_network_name`, `traefik_dashboard_subdomain`, `traefik_base_domain`, `traefik_dashboard_user`, `traefik_dashboard_auth_hash`.
- Produces: Dynamic configuration loaded from `/etc/traefik/dynamic/`, removing all dashboard labels from `docker-compose.yml`.

- [ ] **Step 1: Write failing tests for dynamic provider and label-less Traefik compose**
Add tests to `tests/test_templates_rendering.py`:
- `test_render_traefik_yml_file_provider()`: asserts `providers:` contains `file:` and `directory: "/etc/traefik/dynamic"`.
- `test_render_dynamic_dashboard()`: asserts rendering `dynamic/dashboard.yml.j2` contains `dashboard:` router with rule `Host(traefik.example.com)` and `service: "api@internal"`, and `dash-auth` basicAuth middleware.
- `test_render_docker_compose_traefik_has_no_labels()`: asserts rendered `docker-compose.yml.j2` mounts `/dynamic` and Traefik service does not contain dashboard labels.

- [ ] **Step 2: Run tests to verify they fail**
Run: `pytest tests/test_templates_rendering.py -k "file_provider or dynamic_dashboard or traefik_has_no_labels" -v`
Expected: FAIL

- [ ] **Step 3: Implement dynamic file provider and dashboard configuration**
1. Create `roles/traefik/templates/dynamic/dashboard.yml.j2` with router `dashboard` on `websecure` with `api@internal` service and `dash-auth` middleware.
2. In `roles/traefik/templates/traefik.yml.j2`, add `providers.file` configuration pointing to `/etc/traefik/dynamic` with `watch: true`.
3. In `roles/traefik/templates/docker-compose.yml.j2`, mount `{{ traefik_install_dir }}/dynamic:/etc/traefik/dynamic:ro` into the Traefik container and remove dashboard labels from Traefik container.
4. In `roles/traefik/tasks/main.yml`, add task creating `{{ traefik_install_dir }}/dynamic` directory (`0755`) and deploying `dynamic/dashboard.yml.j2`.

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_templates_rendering.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**
```bash
git add roles/traefik/ templates tests/
git commit -m "feat(traefik): add dynamic file provider and eliminate dashboard labels"
```

---

### Task 3: ACME DNS-01 Challenge & Wildcard Certificates

**Files:**
- Modify: `roles/traefik/defaults/main.yml`
- Modify: `inventory/group_vars/all.yml`
- Modify: `.env.example`
- Modify: `roles/traefik/templates/traefik.yml.j2`
- Modify: `roles/traefik/templates/docker-compose.yml.j2`
- Modify: `roles/traefik/tasks/main.yml`
- Test: `tests/test_templates_rendering.py`

**Interfaces:**
- Consumes: `traefik_acme_challenge_type`, `traefik_acme_dns_provider`, `traefik_acme_dns_resolvers`, `traefik_acme_wildcard_enabled`, `CF_DNS_API_TOKEN`.
- Produces: Automated DNS-01 challenge resolution with wildcard certificates for Cloudflare and generic DNS providers.

- [ ] **Step 1: Write failing tests for DNS-01 challenge and wildcards**
Add tests to `tests/test_templates_rendering.py`:
- `test_render_traefik_yml_dns_challenge_cloudflare()`: asserts `dnsChallenge:`, `provider: cloudflare`, `resolvers:` in rendered static config.
- `test_render_traefik_yml_wildcard_domains()`: asserts `domains:` with `main: example.com` and `sans: ["*.example.com"]` when `traefik_acme_wildcard_enabled=True`.
- `test_render_docker_compose_dns_env_vars()`: asserts `CF_DNS_API_TOKEN` is passed into Traefik environment when DNS challenge is configured.

- [ ] **Step 2: Run tests to verify they fail**
Run: `pytest tests/test_templates_rendering.py -k "dns_challenge or wildcard or dns_env" -v`
Expected: FAIL

- [ ] **Step 3: Implement DNS-01 and wildcard certificate support**
1. In `roles/traefik/defaults/main.yml`: Add `traefik_acme_challenge_type: "http"`, `traefik_acme_dns_provider: "cloudflare"`, `traefik_acme_dns_resolvers: ["1.1.1.1:53", "8.8.8.8:53"]`, `traefik_acme_wildcard_enabled: false`.
2. In `inventory/group_vars/all.yml`: Add resolution for `traefik_cf_dns_api_token` via Vault, `.env`, and shell env.
3. In `roles/traefik/tasks/main.yml`: Add assertion that if `traefik_acme_challenge_type == 'dns'` and provider is `'cloudflare'`, `traefik_cf_dns_api_token` must be defined and non-empty.
4. In `roles/traefik/templates/traefik.yml.j2`: Switch between `dnsChallenge` and `httpChallenge`. When `traefik_acme_wildcard_enabled`, render `domains:` under `entryPoints.websecure.http.tls`.
5. In `roles/traefik/templates/docker-compose.yml.j2`: Pass `CF_DNS_API_TOKEN` into `environment:` when DNS challenge is enabled.
6. Update `.env.example` with commented `CF_DNS_API_TOKEN=...`.

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_templates_rendering.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**
```bash
git add roles/traefik/ inventory/ .env.example tests/
git commit -m "feat(traefik): add ACME DNS-01 challenge and wildcard certificate support"
```

---

### Task 4: Optional Traefik-Level Security Hardening (Socket Proxy & Dynamic Security Middlewares)

**Files:**
- Create: `roles/traefik/templates/dynamic/middlewares.yml.j2`
- Modify: `roles/traefik/defaults/main.yml`
- Modify: `roles/traefik/templates/traefik.yml.j2`
- Modify: `roles/traefik/templates/docker-compose.yml.j2`
- Modify: `roles/traefik/tasks/main.yml`
- Test: `tests/test_templates_rendering.py`

**Interfaces:**
- Consumes: `traefik_socket_proxy_enabled`, `traefik_security_headers_enabled`, `traefik_ratelimit_enabled`.
- Produces: `tecnativa/docker-socket-proxy` container deployment when enabled, and `sec-headers@file` / `rate-limit@file` dynamic middlewares.

- [ ] **Step 1: Write failing tests for socket proxy and security middlewares**
Add tests to `tests/test_templates_rendering.py`:
- `test_render_docker_compose_socket_proxy_enabled()`: asserts `docker-proxy:` service in compose, `CONTAINERS=1`, and Traefik volume does NOT mount `/var/run/docker.sock`.
- `test_render_traefik_yml_socket_proxy_endpoint()`: asserts endpoint is `tcp://docker-proxy:2375` when enabled, and `unix:///var/run/docker.sock` when disabled.
- `test_render_dynamic_middlewares_security_headers()`: asserts `sec-headers` contains `stsSeconds: 31536000`, `contentTypeNosniff: true`, `frameDeny: true`.
- `test_render_traefik_yml_entrypoint_security_headers()`: asserts `entryPoints.websecure.http.middlewares` contains `sec-headers@file` when enabled.

- [ ] **Step 2: Run tests to verify they fail**
Run: `pytest tests/test_templates_rendering.py -k "socket_proxy or middlewares or security_headers" -v`
Expected: FAIL

- [ ] **Step 3: Implement socket proxy and dynamic middlewares**
1. In `roles/traefik/defaults/main.yml`: Add `traefik_socket_proxy_enabled: false`, `traefik_socket_proxy_image: "tecnativa/docker-socket-proxy:latest"`, `traefik_security_headers_enabled: true`, `traefik_ratelimit_enabled: false`.
2. Create `roles/traefik/templates/dynamic/middlewares.yml.j2` with `sec-headers` and `rate-limit`.
3. In `roles/traefik/templates/traefik.yml.j2`:
   - Point docker endpoint to `tcp://docker-proxy:2375` if `traefik_socket_proxy_enabled` else `unix:///var/run/docker.sock`.
   - Add `middlewares: [ "sec-headers@file" ]` under `websecure` entrypoint if `traefik_security_headers_enabled`.
4. In `roles/traefik/templates/docker-compose.yml.j2`:
   - Render `docker-proxy` service when `traefik_socket_proxy_enabled: true`.
   - Mount `/var/run/docker.sock:ro` in Traefik only if `not traefik_socket_proxy_enabled`.
5. In `roles/traefik/tasks/main.yml`: Deploy `dynamic/middlewares.yml.j2`.

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_templates_rendering.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**
```bash
git add roles/traefik/ tests/
git commit -m "feat(traefik): add optional docker socket proxy and security headers middleware"
```

---

### Task 5: Observability & Operational Tools

**Files:**
- Create: `backup_acme.yml`
- Modify: `roles/traefik/defaults/main.yml`
- Modify: `roles/traefik/templates/traefik.yml.j2`
- Modify: `roles/traefik/tasks/main.yml`
- Test: `tests/test_templates_rendering.py`
- Test: `tests/test_role_tasks.py`

**Interfaces:**
- Consumes: `traefik_access_log_enabled`, `traefik_metrics_prometheus_enabled`.
- Produces: JSON access logs, Prometheus metrics endpoint, post-deploy URI healthcheck, and standalone certificate backup playbook.

- [ ] **Step 1: Write failing tests for observability and healthcheck task**
Add tests:
- In `tests/test_templates_rendering.py`: `test_render_traefik_yml_observability_enabled()` asserts `accessLog:` with `format: json` and `metrics:` with `prometheus:`.
- In `tests/test_role_tasks.py`: `test_role_tasks_contain_healthcheck()` asserts `tasks/main.yml` contains `ansible.builtin.uri` polling check.

- [ ] **Step 2: Run tests to verify they fail**
Run: `pytest tests/test_templates_rendering.py tests/test_role_tasks.py -k "observability or healthcheck" -v`
Expected: FAIL

- [ ] **Step 3: Implement observability, healthcheck task, and backup playbook**
1. In `roles/traefik/defaults/main.yml`: Add `traefik_access_log_enabled: false`, `traefik_metrics_prometheus_enabled: false`.
2. In `roles/traefik/templates/traefik.yml.j2`: Render `accessLog` and `metrics.prometheus` blocks when enabled.
3. In `roles/traefik/tasks/main.yml`: Add task waiting for Traefik to respond on HTTP port with `ansible.builtin.uri` (`retries: 12`, `delay: 2`).
4. Create `backup_acme.yml`:
   - Ansible playbook running on `all` with `become: true`.
   - Backup mode: Fetches `{{ traefik_install_dir }}/acme/acme.json` to local `backups/acme-{{ inventory_hostname }}-{{ ansible_date_time.iso8601_basic_short }}.json` with mode `0600`.
   - Restore mode: When `restore_file` is defined, copies local `restore_file` to remote `{{ traefik_install_dir }}/acme/acme.json` with mode `0600` and notifies container restart.

- [ ] **Step 4: Run tests and playbook syntax check**
Run: `pytest tests/ -v && ./tests/test_playbook_syntax.sh && ansible-playbook --syntax-check backup_acme.yml`
Expected: All tests PASS and syntax check succeeds.

- [ ] **Step 5: Commit**
```bash
git add roles/traefik/ backup_acme.yml tests/
git commit -m "feat(traefik): add observability options, healthcheck task, and acme backup playbook"
```

---

### Task 6: Documentation & Example Stack Updates

**Files:**
- Modify: `examples/hello-service/docker-compose.yml`
- Modify: `README.md`
- Test: `tests/run_all_checks.sh`

**Interfaces:**
- Consumes: All features implemented in Tasks 1-5.
- Produces: Updated documentation, streamlined example labels, and green test suite.

- [ ] **Step 1: Streamline example compose labels**
Update `examples/hello-service/docker-compose.yml` to remove redundant TLS/resolver labels and demonstrate the clean 3-line label pattern.

- [ ] **Step 2: Update README.md**
Document:
- ACME DNS-01 Challenge and Cloudflare setup.
- Wildcard certificates (`*.domain.com`).
- Docker Socket Proxy usage (`traefik_socket_proxy_enabled: true`).
- Preconfigured security headers.
- Prometheus metrics & access logging.
- Running certificate backups with `ansible-playbook backup_acme.yml`.
- CI/CD workflow and python requirements.

- [ ] **Step 3: Run entire check suite**
Run: `./tests/run_all_checks.sh`
Expected: 100% green tests and zero syntax errors.

- [ ] **Step 4: Commit**
```bash
git add examples/ README.md
git commit -m "docs: update documentation and example service for v2 enhancements"
```
