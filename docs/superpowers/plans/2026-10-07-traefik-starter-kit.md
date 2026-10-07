# Traefik Starter Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular, reproducible Traefik v3 starter kit for a server container lab, deployed via Ansible, using dynamic SSH inventory, Cloudflare-pointed wildcard subdomains with automated Let's Encrypt TLS, and a pure Docker-label routing model.

**Architecture:** An Ansible role (`roles/traefik`) that creates an external Docker bridge network (`traefik-public`), ensures secure ACME storage (`0600`), templates `traefik.yml` and `docker-compose.yml`, and starts Traefik and an integrated `whoami` verification service. Target hosts are dynamically discovered from `~/.ssh/config` via `ssh_inventory.py`.

**Tech Stack:** Ansible, Python 3, Docker, Docker Compose (v2), Traefik v3, Let's Encrypt ACME.

**Spec:** [docs/superpowers/specs/2026-10-07-traefik-starter-kit-design.md](file:///home/amin/Documents/projects2/traefik-setup-ansible/docs/superpowers/specs/2026-10-07-traefik-starter-kit-design.md)

## Global Constraints

- Must follow the SSH configuration pattern in `/home/amin/Documents/projects/ansible-molecule-oh-my-zsh-example/ansible.cfg` with `ssh_inventory.py`.
- No dynamic file provider: all routing, services, and dashboard auth must be 100% Docker-label driven.
- ACME certificate storage file (`acme.json`) must have strict `0600` permissions.
- Traefik network must be named `traefik-public` and defined as an external network.
- Must provide a lightweight starter example in `examples/hello-service` demonstrating how to connect new services to the lab.

## Review Focus

1. **Missing `~/.ssh/config` or empty host list:** `ssh_inventory.py` must return valid empty JSON `{"_meta": {"hostvars": {}}}` without crashing if `~/.ssh/config` does not exist or has no hosts.
2. **ACME permissions rejection:** Traefik v3 will refuse to boot or request certs if `acme.json` permissions are not exactly `0600`; Ansible task must enforce this explicitly before starting the stack.
3. **Escaping `$` in Basic Auth hashes:** Docker Compose interprets `$` as environment variable interpolation unless escaped as `$$`; Ansible template must ensure bcrypt/apr1 hash dollars are correctly escaped.
4. **Network idempotency:** The `traefik-public` network creation task must succeed whether the network already exists or not.
5. **Missing python Docker SDK on host:** Fallback mechanism or clear task failure message if `docker compose` CLI is used directly instead of requiring specific python libraries.

---

### Task 1: SSH Configuration & Dynamic Inventory Script

**Files:**
- Create: `ansible.cfg`
- Create: `ssh_inventory.py`
- Test: `tests/test_ssh_inventory.py`

**Interfaces:**
- Produces: `ssh_inventory.py` CLI accepting `--list` and `--host <name>` returning JSON inventory.
- Produces: `ansible.cfg` configuring `inventory = ./ssh_inventory.py` and `enable_ssh_config = True`.

- [ ] **Step 1: Write unit test for `ssh_inventory.py`**

Write `tests/test_ssh_inventory.py` testing `--list` flag with a mock SSH config:
```python
import subprocess
import json
import sys

def test_ssh_inventory_list():
    res = subprocess.run([sys.executable, "ssh_inventory.py", "--list"], capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert "_meta" in data
    assert "hostvars" in data["_meta"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_ssh_inventory.py`
Expected: FAIL (file `ssh_inventory.py` not found)

- [ ] **Step 3: Implement `ssh_inventory.py` and `ansible.cfg`**

Create `ssh_inventory.py` with parsing for `~/.ssh/config` and support for `--list` and `--host`. Make executable (`chmod +x ssh_inventory.py`).
Create `ansible.cfg`:
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

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_ssh_inventory.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ansible.cfg ssh_inventory.py tests/test_ssh_inventory.py
git commit -m "feat: add ansible.cfg and dynamic ssh inventory script"
```

---

### Task 2: Inventory Defaults, Central Variables, and Main Playbook

**Files:**
- Create: `inventory/hosts.ini`
- Create: `inventory/group_vars/all.yml`
- Create: `playbook.yml`
- Test: `tests/test_playbook_syntax.sh`

**Interfaces:**
- Consumes: `ssh_inventory.py` or `inventory/hosts.ini`
- Produces: `playbook.yml` entrypoint targeting `all` hosts and invoking role `traefik`.
- Produces: `group_vars/all.yml` central variables for domain, ACME, and dashboard.

- [ ] **Step 1: Write syntax and variables validation script**

Create `tests/test_playbook_syntax.sh`:
```bash
#!/usr/bin/env bash
set -e
ansible-playbook -i inventory/hosts.ini playbook.yml --syntax-check
```
Make executable: `chmod +x tests/test_playbook_syntax.sh`

- [ ] **Step 2: Run test to verify it fails**

Run: `./tests/test_playbook_syntax.sh`
Expected: FAIL (missing files)

- [ ] **Step 3: Implement `inventory/hosts.ini`, `inventory/group_vars/all.yml`, and `playbook.yml`**

1. `inventory/hosts.ini`:
```ini
[all]
# Add static hosts here if not using ~/.ssh/config:
# myserver ansible_host=192.168.1.10 ansible_user=root
```
2. `inventory/group_vars/all.yml`:
Define `traefik_base_domain`, `traefik_acme_email`, `traefik_dashboard_subdomain`, `traefik_dashboard_user`, `traefik_dashboard_password`, `traefik_install_dir`, `traefik_network_name`, `traefik_image_tag`, `traefik_log_level`, `traefik_deploy_whoami`, `traefik_whoami_subdomain`.
3. `playbook.yml`:
```yaml
---
- name: Deploy Traefik Starter Kit Stack
  hosts: all
  become: true
  roles:
    - role: traefik
```

- [ ] **Step 4: Create role scaffold and test syntax**

Create directory `roles/traefik/tasks` and empty `roles/traefik/tasks/main.yml`.
Run: `./tests/test_playbook_syntax.sh`
Expected: PASS (syntax check succeeds)

- [ ] **Step 5: Commit**

```bash
git add inventory/ playbook.yml tests/test_playbook_syntax.sh roles/traefik/tasks/main.yml
git commit -m "feat: add playbook, inventory, and group_vars configuration"
```

---

### Task 3: Traefik Role — Defaults, Static Config, and Docker Compose Templates

**Files:**
- Create: `roles/traefik/defaults/main.yml`
- Create: `roles/traefik/templates/traefik.yml.j2`
- Create: `roles/traefik/templates/docker-compose.yml.j2`
- Create: `roles/traefik/handlers/main.yml`
- Test: `tests/test_templates_rendering.py`

**Interfaces:**
- Consumes: Variables from `defaults/main.yml` and `group_vars/all.yml`.
- Produces: `traefik.yml.j2` (static config) and `docker-compose.yml.j2` (stack with labels and whoami).
- Produces: Restart handler in `roles/traefik/handlers/main.yml`.

- [ ] **Step 1: Write template rendering unit test**

Create `tests/test_templates_rendering.py`:
```python
from jinja2 import Environment, FileSystemLoader

def test_render_traefik_yml():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("traefik.yml.j2")
    rendered = template.render(
        traefik_network_name="traefik-public",
        traefik_acme_email="admin@example.com",
        traefik_log_level="INFO"
    )
    assert "entryPoints:" in rendered
    assert "websecure:" in rendered
    assert "httpChallenge:" in rendered

def test_render_docker_compose():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("docker-compose.yml.j2")
    rendered = template.render(
        traefik_image_tag="v3.1",
        traefik_install_dir="/opt/traefik",
        traefik_network_name="traefik-public",
        traefik_dashboard_subdomain="traefik",
        traefik_base_domain="example.com",
        traefik_dashboard_user="admin",
        traefik_dashboard_auth_hash="$$apr1$$hash",
        traefik_deploy_whoami=True,
        traefik_whoami_subdomain="whoami"
    )
    assert "traefik:" in rendered
    assert "traefik/whoami:latest" in rendered
    assert "traefik-public:" in rendered
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_templates_rendering.py`
Expected: FAIL (templates not found)

- [ ] **Step 3: Implement defaults, templates, and handler**

1. `roles/traefik/defaults/main.yml`: default fallback variables.
2. `roles/traefik/templates/traefik.yml.j2`: static config with `providers.docker` (exposedByDefault: false), `entryPoints.web` (redirects to websecure), `entryPoints.websecure` (certResolver: myresolver), and `certificatesResolvers.myresolver` (httpChallenge on web).
3. `roles/traefik/templates/docker-compose.yml.j2`: Traefik container mounting docker socket (ro), static config (ro), and acme folder (rw); labeled with dashboard router and basicauth middleware. Includes `whoami` container conditional on `traefik_deploy_whoami`.
4. `roles/traefik/handlers/main.yml`:
```yaml
---
- name: Restart traefik stack
  ansible.builtin.command:
    cmd: docker compose down && docker compose up -d
    chdir: "{{ traefik_install_dir }}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_templates_rendering.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add roles/traefik/defaults/ roles/traefik/templates/ roles/traefik/handlers/ tests/test_templates_rendering.py
git commit -m "feat(traefik): add defaults, jinja2 templates, and handlers"
```

---

### Task 4: Traefik Role — Tasks & Idempotent Orchestration

**Files:**
- Modify: `roles/traefik/tasks/main.yml`
- Test: `tests/test_role_tasks.py`

**Interfaces:**
- Consumes: Templates and handlers from Task 3.
- Produces: End-to-end task list for creating network, dirs, acme.json (0600), rendering templates, generating hash, and starting the stack.

- [ ] **Step 1: Write task structure verification test**

Create `tests/test_role_tasks.py` to assert all required task steps exist in `roles/traefik/tasks/main.yml`:
```python
import yaml

def test_tasks_contain_required_steps():
    with open("roles/traefik/tasks/main.yml") as f:
        tasks = yaml.safe_load(f)
    names = [t.get("name", "") for t in tasks]
    assert any("network" in n.lower() for n in names)
    assert any("director" in n.lower() for n in names)
    assert any("acme.json" in n.lower() for n in names)
    assert any("traefik.yml" in n.lower() for n in names)
    assert any("docker-compose.yml" in n.lower() for n in names)
    assert any("deploy" in n.lower() or "stack" in n.lower() for n in names)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_role_tasks.py`
Expected: FAIL (`main.yml` is currently empty)

- [ ] **Step 3: Implement `roles/traefik/tasks/main.yml`**

Implement idempotent tasks:
1. Ensure `traefik_install_dir` and `{{ traefik_install_dir }}/acme` directories exist (`mode: '0755'`).
2. Ensure `{{ traefik_install_dir }}/acme/acme.json` exists with strict permissions (`mode: '0600'`).
3. Ensure Docker network `{{ traefik_network_name }}` exists (using `ansible.builtin.command: docker network create {{ traefik_network_name }}` with `failed_when: false` or `community.docker.docker_network`).
4. Generate dashboard htpasswd password hash if not already provided.
5. Template `traefik.yml` to `{{ traefik_install_dir }}/traefik.yml` (notifies restart handler).
6. Template `docker-compose.yml` to `{{ traefik_install_dir }}/docker-compose.yml` (notifies restart handler).
7. Start/deploy stack with `docker compose up -d` in `{{ traefik_install_dir }}`.

- [ ] **Step 4: Run test and syntax check**

Run: `python3 -m pytest tests/test_role_tasks.py`
Run: `./tests/test_playbook_syntax.sh`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add roles/traefik/tasks/main.yml tests/test_role_tasks.py
git commit -m "feat(traefik): implement role tasks and deployment workflow"
```

---

### Task 5: Lightweight Lab Starter Example & Documentation

**Files:**
- Create: `examples/hello-service/docker-compose.yml`
- Create: `examples/README.md`
- Create: `README.md`
- Test: `tests/test_example_compose.py`

**Interfaces:**
- Produces: A ready-to-run lightweight container compose file for future services.
- Produces: Clear documentation on deploying Traefik and adding new containers.

- [ ] **Step 1: Write test for example compose structure**

Create `tests/test_example_compose.py`:
```python
import yaml

def test_example_compose_validity():
    with open("examples/hello-service/docker-compose.yml") as f:
        doc = yaml.safe_load(f)
    assert "services" in doc
    service = next(iter(doc["services"].values()))
    assert "networks" in service
    assert "traefik-public" in service["networks"]
    assert "labels" in service
    assert any("traefik.enable=true" in l for l in service["labels"])
    assert doc.get("networks", {}).get("traefik-public", {}).get("external") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_example_compose.py`
Expected: FAIL (example file does not exist)

- [ ] **Step 3: Implement example compose and documentation**

1. Create `examples/hello-service/docker-compose.yml`:
A minimal, lightweight web service (`traefik/whoami` or `nginxdemos/hello`) configured with `traefik.enable=true`, `Host(...)`, `entrypoints=websecure`, `tls=true`, and external network `traefik-public`.
2. Create `examples/README.md`: Explaining the 2-step recipe for connecting any new container (Ghost blog, VPN, etc.) to Traefik.
3. Create `README.md`:
   - Quickstart guide (prerequisites, setting variables in `group_vars/all.yml`).
   - Running the playbook with `ansible-playbook -l myserver playbook.yml`.
   - Accessing Traefik dashboard and `whoami`.
   - Troubleshooting tips (DNS propagation, logs with `docker compose logs -f traefik`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_example_compose.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add examples/ README.md tests/test_example_compose.py
git commit -m "docs: add lightweight lab example and quickstart documentation"
```

---

### Task 6: Comprehensive Verification & Linter Pass

**Files:**
- Create: `tests/run_all_checks.sh`
- Test: All tests in `tests/`

- [ ] **Step 1: Implement test runner script `tests/run_all_checks.sh`**

```bash
#!/usr/bin/env bash
set -e
echo "Running pytest..."
python3 -m pytest tests/ -v
echo "Running Ansible syntax check..."
./tests/test_playbook_syntax.sh
echo "All validation checks passed successfully!"
```
Make executable: `chmod +x tests/run_all_checks.sh`

- [ ] **Step 2: Run all checks**

Run: `./tests/run_all_checks.sh`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/run_all_checks.sh
git commit -m "test: add comprehensive test runner and verification suite"
```
