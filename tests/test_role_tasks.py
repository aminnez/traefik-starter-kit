import yaml

def test_tasks_contain_required_steps():
    with open("roles/traefik/tasks/main.yml") as f:
        tasks = yaml.safe_load(f)
    assert tasks is not None and isinstance(tasks, list)
    names = [t.get("name", "") for t in tasks]
    assert any("network" in n.lower() for n in names)
    assert any("director" in n.lower() for n in names)
    assert any("acme.json" in n.lower() for n in names)
    assert any("traefik.yml" in n.lower() for n in names)
    assert any("docker-compose.yml" in n.lower() for n in names)
    assert any("deploy" in n.lower() or "stack" in n.lower() for n in names)


def test_role_tasks_contain_healthcheck():
    with open("roles/traefik/tasks/main.yml") as f:
        tasks = yaml.safe_load(f)
    assert any("ansible.builtin.uri" in t or "uri" in t for t in tasks)

