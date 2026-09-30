# Self-hosted services on `rainbow-flame`: installation plan

Temporary plan for hosting **SparkyFitness**, **Kaneo**, and **Obsidian with LiveSync** on
`rainbow-flame`. It also records where each service lives, so they can be moved to another host
later (see [Migration inventory](#migration-inventory)).

| | |
|---|---|
| Host | `rainbow-flame` (Ubuntu 24.04) |
| Tailnet name | `rainbow-flame.taila02055.ts.net` |
| Tailnet IP | `100.105.75.3` |
| Runtime | Docker + Docker Compose plugin |
| Ingress | `tailscale serve` (HTTPS, tailnet-only, no Funnel) |

---

## 1. Why the current setup shows a blank page

`tailscale serve --set-path=/kaneo http://127.0.0.1:5173` removes the `/kaneo` prefix before
it passes the request to the app. The app doesn't know it has been mounted under `/kaneo`, so the
HTML it returns still points at root paths such as `/assets/useSearch-….js`. The browser then
requests `https://rainbow-flame…/assets/…`, and no serve handler matches that path, so Tailscale
returns a `text/plain` 404. The browser refuses to run that 404 as a JS module, which leaves you
with a blank page and the MIME-type errors.

Kaneo and SparkyFitness are both single-page apps whose builds assume they run at `/`, and
neither has a supported base-path setting. Path-based routing won't work for them.

**Fix: give each service its own HTTPS port on the same MagicDNS name.** `tailscale serve`
accepts any HTTPS port (only Funnel is limited to 443/8443/10000), and the Tailscale-issued cert
covers every port on the host name. Port 443 is left unused, so it's free for a landing page or
another service later.

Every container publishes its port on **loopback only** (`127.0.0.1:<port>`). `tailscale serve`
is the only way in, which always gives you HTTPS. It also avoids a clash where the same port
number is both served by Tailscale and bound by Docker on all interfaces (SparkyFitness uses
3004 for both).

### Port plan

| Service | Local (loopback) | Tailnet URL |
|---|---|---|
| SparkyFitness | `127.0.0.1:3004` | `https://rainbow-flame.taila02055.ts.net:3004/` |
| Kaneo | `127.0.0.1:5173` | `https://rainbow-flame.taila02055.ts.net:8443/` |
| Obsidian (web UI) | `127.0.0.1:3001` (HTTPS, self-signed) | `https://rainbow-flame.taila02055.ts.net:8444/` |
| CouchDB (LiveSync) | `127.0.0.1:5984` | `https://rainbow-flame.taila02055.ts.net:6984/` |

---

## 2. Prerequisites (one time)

```bash
# Docker Engine + compose plugin (skip if `docker compose version` already works)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # log out/in afterwards

# Confirm Tailscale is up and HTTPS certs are enabled for the tailnet
tailscale status
# Admin console → DNS: MagicDNS ON and "HTTPS Certificates" ON

# Common directory for all service configs + data (makes migration a single tree).
# Already exists: SparkyFitness lives in it.
mkdir -p /home/mib/app
```

Clear the broken path-based serve config:

```bash
sudo tailscale serve reset
tailscale serve status   # should report nothing
```

---

## 3. SparkyFitness (already running; re-expose on port 3004)

Installed at `/home/mib/app/sparkyfitness` (`$HOME/app/sparkyfitness`) with Docker Compose.

1. **Bind the frontend to loopback.** In `/home/mib/app/sparkyfitness/docker-compose.yml`, under
   the `sparkyfitness-frontend` service, prefix the port mapping with `127.0.0.1:`:
   ```yaml
     sparkyfitness-frontend:
       ports:
         - "127.0.0.1:${SPARKY_FITNESS_FRONTEND_PORT:-3004}:${NGINX_LISTEN_PORT:-80}"
   ```
   Without this, Docker listens on `0.0.0.0:3004`, including the Tailscale IP, and competes with
   `tailscale serve --https=3004`.
2. **Set the frontend URL** in `/home/mib/app/sparkyfitness/.env`. The server's auth library
   (Better Auth) only accepts logins from this origin, so it has to match what the browser's
   address bar shows **exactly**: `https`, the full MagicDNS name, the `:3004` port, and no
   trailing slash:
   ```env
   SPARKY_FITNESS_FRONTEND_URL=https://rainbow-flame.taila02055.ts.net:3004
   ```
   Make sure this key appears only once in `.env` (`grep -n FRONTEND_URL .env`). If it's defined
   twice, the last one wins.
3. **Recreate the containers:**
   ```bash
   cd /home/mib/app/sparkyfitness
   docker compose up -d
   docker compose ps   # frontend should show 127.0.0.1:3004->…
   curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3004/   # 200
   # confirm the server actually picked up the new origin:
   docker compose exec sparkyfitness-server printenv SPARKY_FITNESS_FRONTEND_URL
   ```
   `docker compose restart` does **not** reload `.env`. Use `up -d`, which recreates any
   container whose environment changed. If `printenv` still shows the old value, run
   `docker compose up -d --force-recreate`.
4. **Expose it on port 3004:**
   ```bash
   sudo tailscale serve --bg --https=3004 http://127.0.0.1:3004
   ```
5. **Verify:** open `https://rainbow-flame.taila02055.ts.net:3004/` from another tailnet device
   and log in. Update any phone bookmarks or home-screen shortcuts that pointed at the old URL
   without a port. In the mobile app, edit the server URL to
   `https://rainbow-flame.taila02055.ts.net:3004`.

#### Troubleshooting: `Authentication Failed: Invalid Origin`

The console shows `403 {"message":"Invalid origin","code":"INVALID_ORIGIN"}`. The server rejected
the login because the request's `Origin` header isn't in its trusted-origins list. That list is
`SPARKY_FITNESS_FRONTEND_URL` plus any entries in `SPARKY_FITNESS_EXTRA_TRUSTED_ORIGINS`. This
happens whenever the URL you use to reach the app changes, for example from
`https://rainbow-flame.taila02055.ts.net` (port 443) or `http://localhost:3004` to the `:3004`
tailnet URL.

1. Compare the origin the browser sends with the one the server trusts:
   ```bash
   # in the browser: dev tools → Network → the failed sign-in request → Request Headers → Origin
   cd /home/mib/app/sparkyfitness
   docker compose exec sparkyfitness-server printenv SPARKY_FITNESS_FRONTEND_URL SPARKY_FITNESS_EXTRA_TRUSTED_ORIGINS
   ```
2. If they differ, fix `SPARKY_FITNESS_FRONTEND_URL` in `.env` (step 2) and run
   `docker compose up -d`. Then hard-reload the page (Cmd-Shift-R) so the browser doesn't reuse a
   cached bundle or stale cookie.
3. If you also reach the app at other URLs, such as the bare IP or `localhost` on the host itself,
   add each one as a comma-separated list. Every entry must be an exact scheme + host + port with
   no trailing slash:
   ```env
   SPARKY_FITNESS_EXTRA_TRUSTED_ORIGINS=http://localhost:3004,https://100.105.75.3:3004
   ```
4. If the mobile app still fails after the browser works, temporarily set
   `SPARKY_FITNESS_LOG_LEVEL=DEBUG`, run `docker compose up -d`, try the login from the app, and
   read `docker compose logs sparkyfitness-server | grep -i origin` to see which origin the app
   sends. Add that exact value to `SPARKY_FITNESS_EXTRA_TRUSTED_ORIGINS`, then set the log level
   back to `ERROR`.

Fresh-install reference (for a future host): download the compose file with
`curl -L -o docker-compose.yml https://raw.githubusercontent.com/CodeWithCJ/SparkyFitness/main/docker/docker-compose.prod.yml`,
fill in `.env` from `.env.simple.example` (`SPARKY_FITNESS_DB_PASSWORD`,
`SPARKY_FITNESS_API_ENCRYPTION_KEY` = `openssl rand -hex 32`, `BETTER_AUTH_SECRET` =
`openssl rand -base64 32`, `SPARKY_FITNESS_FRONTEND_URL`), then run
`docker compose pull && docker compose up -d`.

---

## 4. Kaneo

Current Kaneo runs as a single image (`ghcr.io/usekaneo/kaneo`) that serves both the web UI and
`/api` on port 5173, alongside a Postgres container.

1. **Create the directory and secrets:**
   ```bash
   mkdir -p /home/mib/app/kaneo && cd /home/mib/app/kaneo
   echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
   echo "AUTH_SECRET=$(openssl rand -hex 32)"
   ```
2. **`/home/mib/app/kaneo/.env`:**
   ```env
   KANEO_IMAGE_TAG=2.28.3
   KANEO_CLIENT_URL=https://rainbow-flame.taila02055.ts.net:8443
   POSTGRES_DB=kaneo
   POSTGRES_USER=kaneo
   POSTGRES_PASSWORD=<first secret>
   AUTH_SECRET=<second secret>
   ```
   `KANEO_CLIENT_URL` has to be the exact origin the browser uses, including `:8443`. If it
   doesn't match, logins and cookies fail.
3. **`/home/mib/app/kaneo/compose.yml`** (from the official docs):
   ```yaml
   services:
     postgres:
       image: postgres:16-alpine
       environment:
         POSTGRES_USER: ${POSTGRES_USER:-kaneo}
         POSTGRES_DB: ${POSTGRES_DB:-kaneo}
         POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
       volumes:
         - postgres_data:/var/lib/postgresql/data
       restart: unless-stopped
       healthcheck:
         test: ["CMD-SHELL", 'pg_isready -U "$${POSTGRES_USER}" -d "$${POSTGRES_DB}"']
         interval: 10s
         timeout: 5s
         retries: 5

     kaneo:
       image: ghcr.io/usekaneo/kaneo:${KANEO_IMAGE_TAG:-2.28.3}
       ports:
         - "127.0.0.1:5173:5173"
       env_file:
         - .env
       depends_on:
         postgres:
           condition: service_healthy
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "wget", "-Y", "off", "--quiet", "--spider", "http://127.0.0.1:5173/api/health"]
         interval: 30s
         timeout: 5s
         start_period: 60s
         retries: 3

   volumes:
     postgres_data:
   ```
4. **Start it and expose it:**
   ```bash
   docker compose up -d
   curl -fsS http://127.0.0.1:5173/api/health
   sudo tailscale serve --bg --https=8443 http://127.0.0.1:5173
   ```
5. **Verify:** open `https://rainbow-flame.taila02055.ts.net:8443/`, create the first account,
   and create a workspace.

If you had an earlier Kaneo attempt, it may still be holding port 5173. Run `docker ps` and
remove the stale containers before step 4.

---

## 5. Obsidian (web) + LiveSync

LiveSync syncs through a **CouchDB** server, not through the hosted Obsidian. The phone, the
hosted Obsidian, and any desktop Obsidian are all clients of CouchDB. The hosted Obsidian just
gives you a browser-accessible, always-on vault.

```
 phone Obsidian ─┐
 web Obsidian  ──┼──► CouchDB (https://…:6984) ◄── desktop Obsidian (optional)
                 └─ all sync the same end-to-end-encrypted database
```

### 5a. Remove the `apt`-installed Obsidian

The current install is the desktop app from `apt`. It only shows on the machine's own display,
so other devices can't reach it in a browser. Replace it with the container in 5b.

1. **Back up any vaults it created** (usually none yet, since it was never configured). The
   desktop app lists its vault paths in its config file:
   ```bash
   cat ~/.config/obsidian/obsidian.json 2>/dev/null   # "vaults": { … "path": "…" }
   # copy any listed vault dirs somewhere safe, e.g.
   # cp -a "<vault path>" ~/obsidian-vault-backup/
   ```
2. **Uninstall the package and its settings:**
   ```bash
   apt list --installed 2>/dev/null | grep -i obsidian   # confirm the package name
   sudo apt purge obsidian
   sudo apt autoremove
   rm -rf ~/.config/obsidian   # desktop app settings only; vault dirs are separate
   ```

### 5b. Install Obsidian with Docker

This uses the [`lscr.io/linuxserver/obsidian`](https://docs.linuxserver.io/images/docker-obsidian/)
image, which runs the Obsidian desktop app inside the container and streams it to a browser tab.

1. **Create the directory and look up your IDs:**
   ```bash
   mkdir -p /home/mib/app/obsidian/config && cd /home/mib/app/obsidian
   id -u; id -g   # use these for PUID / PGID below
   ```
2. **`/home/mib/app/obsidian/.env`:**
   ```env
   PUID=1000
   PGID=1000
   TZ=America/Los_Angeles
   OBSIDIAN_USER=mib
   OBSIDIAN_PASSWORD=<openssl rand -hex 16>
   ```
   `OBSIDIAN_USER` and `OBSIDIAN_PASSWORD` are the basic-auth login for the web UI.
3. **`/home/mib/app/obsidian/compose.yml`:**
   ```yaml
   services:
     obsidian:
       image: lscr.io/linuxserver/obsidian:latest
       container_name: obsidian
       security_opt:
         - seccomp:unconfined
       environment:
         - PUID=${PUID}
         - PGID=${PGID}
         - TZ=${TZ}
         - CUSTOM_USER=${OBSIDIAN_USER}
         - PASSWORD=${OBSIDIAN_PASSWORD}
       volumes:
         - ./config:/config         # vaults + Obsidian settings live here
       ports:
         - "127.0.0.1:3001:3001"    # HTTPS (self-signed) web UI
       shm_size: "1gb"
       restart: unless-stopped
   ```
4. **Start it and expose it:**
   ```bash
   docker compose up -d
   docker compose logs -f obsidian   # wait for the web server to come up, then Ctrl-C
   # upstream is self-signed HTTPS, so tell serve not to verify it
   sudo tailscale serve --bg --https=8444 https+insecure://127.0.0.1:3001
   ```
5. **Verify:** open `https://rainbow-flame.taila02055.ts.net:8444/`, log in with the basic-auth
   credentials, and confirm the Obsidian window appears. Create a vault under the container's
   `/config` path so it's stored in `/home/mib/app/obsidian/config/` on the host. If you backed
   up a vault in 5a, copy it into `/home/mib/app/obsidian/config/` first and open it as an
   existing vault.

Upgrading: `docker compose pull && docker compose up -d`. The data in `./config` stays in place.

### 5c. CouchDB for LiveSync (`/home/mib/app/couchdb/`)

1. **Compose file** (`/home/mib/app/couchdb/compose.yml`):
   ```yaml
   services:
     couchdb:
       image: couchdb:3
       container_name: couchdb-livesync
       environment:
         - COUCHDB_USER=${COUCHDB_USER}
         - COUCHDB_PASSWORD=${COUCHDB_PASSWORD}
       volumes:
         - ./data:/opt/couchdb/data
         - ./etc:/opt/couchdb/etc/local.d
       ports:
         - "127.0.0.1:5984:5984"
       restart: unless-stopped
   ```
   `.env` in the same directory:
   ```env
   COUCHDB_USER=livesync-admin
   COUCHDB_PASSWORD=<openssl rand -hex 24>
   ```
2. **Start it and provision it for LiveSync.** The init script sets single-node mode,
   `require_valid_user`, CORS for `app://obsidian.md` / `capacitor://localhost` /
   `http://localhost`, and the request-size limits:
   ```bash
   cd /home/mib/app/couchdb && docker compose up -d
   # the upstream provisioning script requires Deno 2
   curl -fsSL https://deno.land/install.sh | sh
   export hostname=http://127.0.0.1:5984
   export username=livesync-admin
   export password=<COUCHDB_PASSWORD>
   export database=obsidiannotes
   curl -s https://raw.githubusercontent.com/vrtmrz/obsidian-livesync/main/utils/couchdb/couchdb-init.sh | bash
   # expect: "CouchDB provisioning completed."
   ```
3. **Expose it over HTTPS.** Obsidian mobile requires a valid certificate. The Tailscale cert is
   valid, and this stays tailnet-only, so no internet exposure is needed:
   ```bash
   sudo tailscale serve --bg --https=6984 http://127.0.0.1:5984
   curl -u livesync-admin:<pw> https://rainbow-flame.taila02055.ts.net:6984/_up   # {"status":"ok"}
   ```
4. **Generate a Setup URI** (works on any machine with Deno):
   ```bash
   export hostname=https://rainbow-flame.taila02055.ts.net:6984
   export database=obsidiannotes
   export username=livesync-admin
   export password=<COUCHDB_PASSWORD>
   export passphrase=<vault E2E encryption passphrase — store it in your password manager>
   deno run --minimum-dependency-age=0 --allow-env \
     https://raw.githubusercontent.com/vrtmrz/obsidian-livesync/main/utils/setup/generate_setup_uri.ts
   ```
   Save the `obsidian://setuplivesync?settings=…` URI and the passphrase it prints, both in your
   password manager.

### 5d. Connect the clients

1. **Web Obsidian (first, since it seeds the database):** open the vault → Settings → Community
   plugins → turn on community plugins → Browse → install and enable **Self-hosted LiveSync** →
   run the command palette's "Use the copied setup URI" (or the plugin's setup wizard) → paste
   the URI and passphrase → choose that this device is the **first/main** device and let it
   upload.
2. **Phone:** make sure the Tailscale app is connected → install Obsidian → create an empty vault
   with the same name → install and enable Self-hosted LiveSync → apply the same setup URI →
   choose to fetch from the remote.
3. **Verify:** edit a note on the phone and confirm the change appears in the web UI within a few
   seconds, then test the reverse direction.

---

## 6. Final serve config and checks

```bash
tailscale serve status
```

Expected output, roughly:

```
https://rainbow-flame.taila02055.ts.net:3004 (tailnet only)
|-- / proxy http://127.0.0.1:3004
https://rainbow-flame.taila02055.ts.net:8443 (tailnet only)
|-- / proxy http://127.0.0.1:5173
https://rainbow-flame.taila02055.ts.net:8444 (tailnet only)
|-- / proxy https+insecure://127.0.0.1:3001
https://rainbow-flame.taila02055.ts.net:6984 (tailnet only)
|-- / proxy http://127.0.0.1:5984
```

`--bg` keeps the config across reboots. Docker's `restart: unless-stopped` covers the
containers. After a reboot, run `tailscale serve status` and `docker ps` to confirm everything
came back.

---

## Migration inventory

Keep this table accurate. It's the checklist for moving everything to a new host.

| Service | Config dir | Persistent data | Secrets (in `.env`) | Host-specific values to change | Serve rule |
|---|---|---|---|---|---|
| SparkyFitness | `/home/mib/app/sparkyfitness` | Postgres + uploads (check `docker-compose.yml` for volume/bind names) | DB password, API encryption key, `BETTER_AUTH_SECRET` | `SPARKY_FITNESS_FRONTEND_URL`, `SPARKY_FITNESS_EXTRA_TRUSTED_ORIGINS`; loopback bind in `docker-compose.yml` | `:3004 → 127.0.0.1:3004` |
| Kaneo | `/home/mib/app/kaneo` | Docker volume `kaneo_postgres_data` | `POSTGRES_PASSWORD`, `AUTH_SECRET` | `KANEO_CLIENT_URL` | `:8443 → 127.0.0.1:5173` |
| Obsidian web | `/home/mib/app/obsidian` | `./config` (vault + app settings) | `OBSIDIAN_PASSWORD` | none (URL only in bookmarks) | `:8444 → https+insecure://127.0.0.1:3001` |
| CouchDB | `/home/mib/app/couchdb` | `./data`, `./etc` | `COUCHDB_PASSWORD`, LiveSync E2E passphrase | Setup URI `hostname` (regenerate it; re-apply on each client) | `:6984 → 127.0.0.1:5984` |

### Moving to a new host

1. On the old host, run `docker compose down` in each `/home/mib/app/*` directory.
2. Dump the databases that live in named volumes: for Kaneo, run
   `docker compose exec postgres pg_dump -U kaneo kaneo > kaneo.sql` (before the `down`), and do
   the same for SparkyFitness's Postgres.
3. Copy all of `/home/mib/app/` with `rsync -aHAX`, which preserves ownership for bind mounts.
4. Restore the dumps into the new Postgres containers.
5. Update the host-specific URLs in the table above, run `docker compose up -d`, and re-run the
   `tailscale serve` commands.
6. If the host name changed, regenerate the LiveSync Setup URI and re-apply it on every client.
   The data in CouchDB carries over as-is.
7. Remove the old host's serve config with `sudo tailscale serve reset`.
