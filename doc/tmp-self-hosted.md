# Self-hosted services on `rainbow-flame`: installation plan

Temporary plan for hosting **SparkyFitness**, **Kaneo**, and **AFFiNE** on `rainbow-flame`. It also records where each service lives, so they can be moved to another host
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
| AFFiNE | `127.0.0.1:3010` | `https://rainbow-flame.taila02055.ts.net:8444/` |

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

## 5. AFFiNE (docs, notes, whiteboards)

AFFiNE is the self-hosted documentation tool: a Notion-style doc editor plus a Miro-style canvas,
in the browser and in native iOS/Android apps that connect to this server. See
[Appendix: documentation tool comparison](#appendix-documentation-tool-comparison) for why it was
picked and what to fall back to.

The stack is four containers from AFFiNE's official self-host compose file (release `v0.27.4`):
`affine_server` (web UI + API), a one-shot `affine_migration` job, Postgres (with pgvector), and
Redis.

### 5a. Tear down the Obsidian attempt

Skip any command whose target doesn't exist.

```bash
# Obsidian web container (and CouchDB, if you got as far as LiveSync)
cd /home/mib/app/obsidian && docker compose down
cd /home/mib/app/couchdb 2>/dev/null && docker compose down
sudo tailscale serve --https=8444 off
sudo tailscale serve --https=6984 off 2>/dev/null
# Keep any notes you want to carry over, then delete the dirs
ls /home/mib/app/obsidian/config
rm -rf /home/mib/app/obsidian /home/mib/app/couchdb
# The apt-installed desktop app, if it's still there
sudo apt purge obsidian && sudo apt autoremove
```

### 5b. Install

1. **Create the directory** and pull the official compose file, pinned to a release:
   ```bash
   mkdir -p /home/mib/app/affine/{config,data} && cd /home/mib/app/affine
   curl -fsSL -o compose.yml \
     https://github.com/toeverything/affine/releases/download/v0.27.4/docker-compose.yml
   ```
2. **Edit `compose.yml`** in two places:
   - Bind the server to loopback. Under `affine:`, change `'3010:3010'` to:
     ```yaml
         ports:
           - '127.0.0.1:3010:3010'
     ```
   - Pin the image by replacing both `ghcr.io/toeverything/affine:stable` lines with
     `ghcr.io/toeverything/affine:${AFFINE_REVISION:-stable}`. Then `AFFINE_REVISION` in `.env`
     controls upgrades.

   Leave the rest as shipped. Postgres uses `trust` auth, which is safe here only because it
   publishes no ports and is reachable only on the compose network.
3. **`/home/mib/app/affine/.env`:**
   ```env
   AFFINE_REVISION=stable
   TZ=America/Los_Angeles
   ```
4. **`/home/mib/app/affine/config/config.json`.** This sets the public URL. It has to match the
   URL the browser and apps use, port included. If it doesn't, links, invites, and sign-in
   redirects break.
   ```json
   {
     "$schema": "https://github.com/toeverything/affine/releases/latest/download/config.schema.json",
     "server": {
       "name": "rainbow-flame",
       "externalUrl": "https://rainbow-flame.taila02055.ts.net:8444"
     }
   }
   ```
5. **Start it.** The migration job runs first and exits, then the server starts:
   ```bash
   docker compose up -d
   docker compose ps -a        # affine_migration_job: Exited (0); affine_server: Up
   docker compose logs -f affine   # wait for the server to report it's listening, then Ctrl-C
   curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3010/   # 200
   ```
6. **Expose it** (AFFiNE syncs over WebSockets, which `tailscale serve` proxies automatically):
   ```bash
   sudo tailscale serve --bg --https=8444 http://127.0.0.1:3010
   ```
7. **Create the admin account.** Open `https://rainbow-flame.taila02055.ts.net:8444/` from
   another tailnet device. A fresh server sends you to the admin setup (`/admin`). Create the
   first account there; it becomes the server admin. Then create a workspace and **choose this
   server as its location, not "local"**. Local workspaces live only in that browser.
8. **Connect the phone:** make sure the Tailscale app is connected → install AFFiNE from the App
   Store / Play Store → sign in → add a self-hosted server with
   `https://rainbow-flame.taila02055.ts.net:8444` → log in with the account from step 7.
9. **Verify:** edit a doc on the phone and confirm the change appears in the desktop browser
   within a few seconds, then test the reverse direction and a whiteboard (edgeless) page.

### 5c. LLM / MCP access (optional, later)

AFFiNE has a built-in MCP server (Settings → Integrations → MCP Server). It's read-only by
default, and on self-hosted installs it needs **AI features enabled**, which means configuring
an LLM provider under the `copilot` section of `config.json` or in the admin panel. Until then,
community MCP servers that use AFFiNE's API are an alternative (e.g.
[`DAWNCR0W/affine-mcp-server`](https://github.com/DAWNCR0W/affine-mcp-server)).

### 5d. Upgrading

Back up first (see [Moving to a new host](#moving-to-a-new-host), step 2), then:

```bash
cd /home/mib/app/affine
# set AFFINE_REVISION in .env if pinned, then:
docker compose pull && docker compose up -d   # migration job runs again automatically
```

Also grab the newer release's `docker-compose.yml` and diff it against yours, keeping your two
edits from step 2.

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
|-- / proxy http://127.0.0.1:3010
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
| AFFiNE | `/home/mib/app/affine` | `./data/postgres`, `./data/storage` (uploads/blobs), `./config` | none by default (Postgres uses trust auth); LLM API key if AI is enabled | `server.externalUrl` in `config/config.json`; server URL in each mobile app; loopback bind in `compose.yml` | `:8444 → 127.0.0.1:3010` |

### Moving to a new host

1. On the old host, run `docker compose down` in each `/home/mib/app/*` directory.
2. Before the `down`, dump every Postgres database:
   - Kaneo: `docker compose exec postgres pg_dump -U kaneo kaneo > kaneo.sql`
   - AFFiNE: `docker compose exec postgres pg_dump -U affine affine > affine.sql`
   - SparkyFitness: do the same for its Postgres.

   Bind-mounted data dirs copy fine when the stack is stopped, but a dump is the version-safe
   backup.
3. Copy all of `/home/mib/app/` with `rsync -aHAX`, which preserves ownership for bind mounts.
4. Restore the dumps into the new Postgres containers.
5. Update the host-specific URLs in the table above, run `docker compose up -d`, and re-run the
   `tailscale serve` commands.
6. If the host name changed, update AFFiNE's `externalUrl` and re-add the server in the AFFiNE
   mobile app.
7. Remove the old host's serve config with `sudo tailscale serve reset`.

---

## Appendix: documentation tool comparison

**Decision (2026-09): AFFiNE.** Obsidian was tried and rejected. Its "self-hosted" mode is the
desktop app streamed into a browser tab (plus a separate CouchDB for LiveSync), and the setup
felt clumsy and fragile. AFFiNE won because it has a native mobile app that connects to a
self-hosted server, plus a Miro-style canvas.

**Fallback plan:** if AFFiNE doesn't work out, try **Outline**, then **Docmost**, and/or
**BookStack**. All three are Docker Compose installs that fit the same pattern as §5 (loopback
port, `tailscale serve` on `:8444`).

### Requirements

- Source of truth for docs across projects (sdlc-llm, personal notes, …)
- WYSIWYG in-browser editor
- Usable from a desktop browser and from mobile
- Ideally a native mobile app that talks to the self-hosted server; otherwise a solid mobile web UI
- Easy for LLM agents to use (MCP)
- Stable, with an active community
- Nice to have: plugins/extensions
- Reference points: Notion, Confluence

### Scorecard

Legend: ✅ strong, 🟡 partial or with caveats, ❌ missing.

| | AFFiNE | Outline | Docmost | BookStack | AppFlowy | TriliumNext | Obsidian |
|---|---|---|---|---|---|---|---|
| Feels like | Notion + whiteboard | Notion + Confluence | Confluence | Structured wiki | Notion | Personal notes tree | Local markdown vault |
| WYSIWYG in the browser | ✅ | ✅ | ✅ | ✅ (older-style editor) | ✅ | ✅ | ❌ streamed desktop app only |
| Mobile web | 🟡 | 🟡 good for reading, OK for editing | 🟡 | 🟡 fine | 🟡 | 🟡 separate mobile layout | ❌ |
| Native app for your own server | ✅ iOS/Android | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ but syncs via LiveSync, not the server |
| LLM / MCP access | 🟡 built-in, but self-hosted needs AI features on; read-only by default | ✅ built-in `/mcp` endpoint, works self-hosted | 🟡 built-in one needs a paid licence; community servers use the free API | 🟡 community server over a solid REST API | 🟡 community | 🟡 API + community | 🟡 via a community plugin, or just read the files |
| Stability | 🟡 rapid releases, rough edges | ✅ mature, several years in production | 🟡 young (2024), moving fast | ✅ very mature (2015–) | 🟡 complex server stack | ✅ | ✅ app, 🟡 self-hosted setup |
| Community | ✅ large | ✅ large | 🟡 growing fast | ✅ steady | ✅ large | 🟡 | ✅ huge |
| Plugins | 🟡 limited | ❌ integrations only | ❌ | 🟡 theme/hook system | ❌ | ✅ scripting | ✅ best in class |
| Multiple projects | ✅ workspaces | ✅ collections + permissions | ✅ spaces + permissions | ✅ shelves/books | ✅ workspaces | 🟡 one tree | 🟡 one vault per project |
| Setup effort | ✅ Docker Compose | 🟡 needs a login provider (OIDC/Google/Slack, or email via SMTP) | ✅ Docker Compose, simple | ✅ simple | ❌ many services | ✅ one container | ❌ |
| Licence | Open source (MIT) + paid tier | Source-available (BSL; self-hosting allowed) | Open source (AGPL) | Open source (MIT) | Open source (AGPL) | Open source (AGPL) | Proprietary app, open file format |

Left out because they don't let you edit in the browser: Joplin, Anytype, Logseq. Notion and
Confluence themselves can't realistically be self-hosted (Confluence Data Center is
enterprise-priced).

### Notes on the fallbacks

- **Outline**
  - The closest to Notion, in both editing and organisation (collections, nested docs).
  - Its built-in MCP server works on self-hosted installs without a paid tier (Settings → AI),
    and it has a good REST API.
  - Costs: you must set up a login provider (a self-hosted OIDC provider such as Pocket ID,
    Authentik, or Authelia fits the home-network plan), and there's no native mobile app.
- **Docmost**
  - The most Confluence-like: spaces, page trees, permissions, and built-in diagrams (draw.io,
    Excalidraw, Mermaid).
  - The easiest of the three to install.
  - Its built-in MCP server needs the paid Business licence, so you'd use a community MCP server.
  - It's younger than Outline, so a bigger bet on longevity.
- **BookStack**
  - Very stable, easy to run, with a good API and a capable community MCP server.
  - The trade-off is a traditional wiki look and feel, not Notion's.

Whichever tool is in use, sdlc-llm's `.tasks/` specs stay as markdown in the repo, because the
workflow depends on them. The docs tool holds notes and longer-form docs, reached by agents over
MCP.

Sources (checked 2026-09):
[Outline MCP guide](https://mcp.directory/blog/outline-mcp-complete-guide-2026),
[Docmost MCP docs](https://docmost.com/docs/user-guide/mcp),
[docmost-mcp-oss](https://github.com/abelsr/docmost-mcp-oss),
[AFFiNE MCP](https://affine.pro/mcp),
[AFFiNE self-host](https://affine.pro/self-host),
[bookstack-mcp-server](https://github.com/pnocera/bookstack-mcp-server).
