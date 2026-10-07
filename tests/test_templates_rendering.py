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

def test_render_traefik_yml_with_sablier():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("traefik.yml.j2")
    rendered = template.render(
        traefik_network_name="traefik-public",
        traefik_acme_email="admin@example.com",
        traefik_log_level="INFO",
        traefik_sablier_enabled=True,
        traefik_sablier_plugin_version="v1.3.1"
    )
    assert "experimental:" in rendered
    assert "plugins:" in rendered
    assert "github.com/sablierapp/sablier-traefik-plugin" in rendered
    assert "v1.3.1" in rendered

def test_render_traefik_yml_without_sablier():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("traefik.yml.j2")
    rendered = template.render(
        traefik_network_name="traefik-public",
        traefik_acme_email="admin@example.com",
        traefik_log_level="INFO",
        traefik_sablier_enabled=False
    )
    assert "sablier" not in rendered

def test_render_docker_compose_default():
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
        traefik_whoami_subdomain="whoami",
        traefik_sablier_enabled=False
    )
    assert "traefik:" in rendered
    assert "traefik/whoami:latest" in rendered
    assert "traefik-public:" in rendered
    assert "sablier:" not in rendered
    assert "sablier.enable=true" not in rendered

def test_render_docker_compose_with_sablier():
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
        traefik_whoami_subdomain="whoami",
        traefik_sablier_enabled=True,
        traefik_sablier_image="sablierapp/sablier:latest",
        traefik_sablier_url="http://sablier:10000",
        traefik_sablier_default_session_duration="5m",
        traefik_sablier_default_theme="hacker-terminal",
        traefik_whoami_sablier_enabled=True,
        traefik_whoami_sablier_group="whoami",
        traefik_whoami_sablier_session_duration="5m",
        traefik_whoami_sablier_display_name="Whoami Service",
        traefik_whoami_sablier_theme="hacker-terminal"
    )
    assert "sablier:" in rendered
    assert "sablierapp/sablier:latest" in rendered
    assert "start" in rendered
    assert "--provider.name=docker" in rendered
    assert "sablier.enable=true" in rendered
    assert "sablier.group=whoami" in rendered
    assert "traefik.docker.allownonrunning=true" in rendered
    assert "traefik.http.routers.whoami.middlewares=whoami-sablier"


def test_render_traefik_yml_file_provider():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("traefik.yml.j2")
    rendered = template.render(
        traefik_network_name="traefik-public",
        traefik_acme_email="admin@example.com",
        traefik_log_level="INFO"
    )
    assert "file:" in rendered
    assert 'directory: "/etc/traefik/dynamic"' in rendered
    assert "watch: true" in rendered


def test_render_dynamic_dashboard():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("dynamic/dashboard.yml.j2")
    rendered = template.render(
        traefik_dashboard_subdomain="traefik",
        traefik_base_domain="example.com",
        traefik_dashboard_user="admin",
        traefik_dashboard_auth_hash="$apr1$hash"
    )
    assert "Host(`traefik.example.com`)" in rendered
    assert "service: api@internal" in rendered or "service: \"api@internal\"" in rendered
    assert "dash-auth" in rendered
    assert "admin:$apr1$hash" in rendered


def test_render_docker_compose_traefik_has_no_dashboard_labels():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("docker-compose.yml.j2")
    rendered = template.render(
        traefik_image_tag="v3.1",
        traefik_install_dir="/opt/traefik",
        traefik_network_name="traefik-public",
        traefik_deploy_whoami=False,
        traefik_sablier_enabled=False
    )
    assert "/opt/traefik/dynamic:/etc/traefik/dynamic:ro" in rendered
    assert "traefik.http.routers.dashboard" not in rendered


def test_render_traefik_yml_dns_challenge_cloudflare():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("traefik.yml.j2")
    rendered = template.render(
        traefik_network_name="traefik-public",
        traefik_acme_email="admin@example.com",
        traefik_acme_challenge_type="dns",
        traefik_acme_dns_provider="cloudflare",
        traefik_acme_dns_resolvers=["1.1.1.1:53", "8.8.8.8:53"],
        traefik_log_level="INFO"
    )
    assert "dnsChallenge:" in rendered
    assert 'provider: "cloudflare"' in rendered or "provider: cloudflare" in rendered
    assert "1.1.1.1:53" in rendered
    assert "8.8.8.8:53" in rendered
    assert "httpChallenge:" not in rendered


def test_render_traefik_yml_wildcard_domains():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("traefik.yml.j2")
    rendered = template.render(
        traefik_network_name="traefik-public",
        traefik_acme_email="admin@example.com",
        traefik_acme_challenge_type="dns",
        traefik_base_domain="example.com",
        traefik_acme_wildcard_enabled=True,
        traefik_log_level="INFO"
    )
    assert "domains:" in rendered
    assert "main: example.com" in rendered or 'main: "example.com"' in rendered
    assert "*.example.com" in rendered


def test_render_docker_compose_dns_env_vars():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("docker-compose.yml.j2")
    rendered = template.render(
        traefik_image_tag="v3.1",
        traefik_install_dir="/opt/traefik",
        traefik_network_name="traefik-public",
        traefik_acme_challenge_type="dns",
        traefik_cf_dns_api_token="cf-secret-token-12345",
        traefik_deploy_whoami=False,
        traefik_sablier_enabled=False
    )
    assert "CF_DNS_API_TOKEN=cf-secret-token-12345" in rendered or "CF_DNS_API_TOKEN: cf-secret-token-12345" in rendered


def test_render_docker_compose_socket_proxy_enabled():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("docker-compose.yml.j2")
    rendered = template.render(
        traefik_image_tag="v3.1",
        traefik_install_dir="/opt/traefik",
        traefik_network_name="traefik-public",
        traefik_socket_proxy_enabled=True,
        traefik_socket_proxy_image="tecnativa/docker-socket-proxy:latest",
        traefik_deploy_whoami=False,
        traefik_sablier_enabled=False
    )
    assert "docker-proxy:" in rendered
    assert "tecnativa/docker-socket-proxy:latest" in rendered
    assert "CONTAINERS=1" in rendered
    assert "- /var/run/docker.sock:/var/run/docker.sock:ro" in rendered
    # Traefik itself must not mount the docker socket when proxy is enabled
    traefik_section = rendered.split("docker-proxy:")[0]
    assert "- /var/run/docker.sock:/var/run/docker.sock" not in traefik_section


def test_render_traefik_yml_socket_proxy_endpoint():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("traefik.yml.j2")
    
    # Test proxy enabled
    rendered_enabled = template.render(
        traefik_network_name="traefik-public",
        traefik_acme_email="admin@example.com",
        traefik_socket_proxy_enabled=True
    )
    assert 'endpoint: "tcp://docker-proxy:2375"' in rendered_enabled
    
    # Test proxy disabled
    rendered_disabled = template.render(
        traefik_network_name="traefik-public",
        traefik_acme_email="admin@example.com",
        traefik_socket_proxy_enabled=False
    )
    assert 'endpoint: "unix:///var/run/docker.sock"' in rendered_disabled


def test_render_dynamic_middlewares_security_headers():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("dynamic/middlewares.yml.j2")
    rendered = template.render(
        traefik_security_headers_enabled=True,
        traefik_ratelimit_enabled=True,
        traefik_ratelimit_average=100,
        traefik_ratelimit_burst=50
    )
    assert "sec-headers:" in rendered
    assert "stsSeconds: 31536000" in rendered
    assert "contentTypeNosniff: true" in rendered
    assert "frameDeny: true" in rendered
    assert "rate-limit:" in rendered
    assert "average: 100" in rendered
    assert "burst: 50" in rendered


def test_render_traefik_yml_entrypoint_security_headers():
    env = Environment(loader=FileSystemLoader("roles/traefik/templates"))
    template = env.get_template("traefik.yml.j2")
    rendered = template.render(
        traefik_network_name="traefik-public",
        traefik_acme_email="admin@example.com",
        traefik_security_headers_enabled=True
    )
    assert "middlewares:" in rendered
    assert "sec-headers@file" in rendered


