# Adding Containers to Your Lab

Traefik dynamically discovers and manages certificates for any container running on your server with **zero configuration changes** to Traefik itself.

## The 2-Step Recipe

To add any service (blog, VPN web UI, dashboard, database admin, etc.):

### 1. Attach to the `traefik-public` network
Declare `traefik-public` as external and attach your service to it:

```yaml
networks:
  traefik-public:
    external: true
```

### 2. Add Traefik labels
Add routing and TLS labels under your service definition:

```yaml
services:
  myservice:
    image: my-image:tag
    networks:
      - traefik-public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myservice.rule=Host(`myservice.yourdomain.com`)"
      - "traefik.http.routers.myservice.entrypoints=websecure"
      - "traefik.http.routers.myservice.tls=true"
      - "traefik.http.routers.myservice.tls.certresolver=myresolver"
      - "traefik.http.services.myservice.loadbalancer.server.port=PORT_CONTAINER_LISTENS_ON"
```

### Example: Running Ghost Blog
```yaml
services:
  ghost:
    image: ghost:5-alpine
    restart: unless-stopped
    environment:
      url: https://blog.yourdomain.com
    volumes:
      - ghost-content:/var/lib/ghost/content
    networks:
      - traefik-public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.blog.rule=Host(`blog.yourdomain.com`)"
      - "traefik.http.routers.blog.entrypoints=websecure"
      - "traefik.http.routers.blog.tls=true"
      - "traefik.http.routers.blog.tls.certresolver=myresolver"
      - "traefik.http.services.blog.loadbalancer.server.port=2368"

volumes:
  ghost-content:

networks:
  traefik-public:
    external: true
```

Run `docker compose up -d` in the service directory, and Traefik will immediately route traffic and obtain an automated SSL certificate.
