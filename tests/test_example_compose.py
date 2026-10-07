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
