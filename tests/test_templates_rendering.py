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
