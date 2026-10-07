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

---

## Scale-to-Zero on Demand (Sablier)

If you have services that are rarely used (e.g. admin panels, test environments, analytics dashboards), you can have Docker automatically stop them when idle and start them on demand when someone visits the URL.

### Generic Sablier Configuration
The starter kit deploys a shared Sablier daemon reachable on the `traefik-public` network at `http://sablier:10000` with the Traefik `sablier-traefik-plugin` registered.

To enable scale-to-zero on any custom container, add the following labels:

```yaml
services:
  my-app:
    image: my-image:tag
    restart: unless-stopped
    networks:
      - traefik-public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`myapp.yourdomain.com`)"
      - "traefik.http.routers.myapp.entrypoints=websecure"
      - "traefik.http.routers.myapp.tls=true"
      - "traefik.http.routers.myapp.tls.certresolver=myresolver"
      - "traefik.http.services.myapp.loadbalancer.server.port=80"

      # --- Sablier Scale-to-Zero Configuration ---
      - "sablier.enable=true"
      - "sablier.group=myapp"
      - "traefik.docker.allownonrunning=true"
      - "traefik.http.middlewares.myapp-sablier.plugin.sablier.sablierUrl=http://sablier:10000"
      - "traefik.http.middlewares.myapp-sablier.plugin.sablier.group=myapp"
      - "traefik.http.middlewares.myapp-sablier.plugin.sablier.sessionDuration=5m"
      - "traefik.http.middlewares.myapp-sablier.plugin.sablier.dynamic.displayName=My App"
      - "traefik.http.middlewares.myapp-sablier.plugin.sablier.dynamic.theme=hacker-terminal"
      - "traefik.http.routers.myapp.middlewares=myapp-sablier"

networks:
  traefik-public:
    external: true
```

### How it works:
1. **Initial / Idle State**: Sablier keeps the container stopped (`docker stop`).
2. **First Request**: When a user visits `https://myapp.yourdomain.com`, Traefik's Sablier middleware intercepts the request and serves a loading screen (e.g. `hacker-terminal` theme).
3. **Automatic Startup**: Sablier triggers Docker to start `my-app`.
4. **Transparent Pass-Through**: Once the container is healthy/ready, the loading page refreshes and displays your app.
5. **Auto-Stop After Inactivity**: Once no requests are received for `sessionDuration` (e.g., 5 minutes), Sablier safely stops the container again to conserve server RAM and CPU.
