# Self-hosted services on `rainbow-flame`: installation plan

Temporary plan for hosting **SparkyFitness**, **Kaneo**, **AFFiNE**, and **Outline** (on trial,
with **Pocket ID** for sign-in) on `rainbow-flame`. It also records where each service lives, so
they can be moved to another host later (see [Migration inventory](#migration-inventory)).

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
| Outline | `127.0.0.1:3000` | `https://rainbow-flame.taila02055.ts.net:8445/` |
| Pocket ID (sign-in for Outline) | `127.0.0.1:1411` | `https://rainbow-flame.taila02055.ts.net:8446/` |

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
   curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3010/
   # 302 on a fresh server (it redirects to the initial admin setup); 200 once set up
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

### 5c. LLM agent access (MCP)

**Verdict (checked against AFFiNE `v0.27.4` source, 2026-09-30):**

| Option | Read | Create / update | Needs an AI provider key? | Use it? |
|---|---|---|---|---|
| A. Built-in MCP server | ✅ `read_document`, `doc_search` | ❌ write tools are compiled in but only registered on dev/canary builds | No; only the `copilot.enabled` switch | Read-only fallback |
| B. [`DAWNCR0W/affine-mcp-server`](https://github.com/DAWNCR0W/affine-mcp-server) | ✅ | ✅ (Markdown create, append, block edits, databases, canvas) | No | **Yes, primary** |

Why the built-in server is read-only on self-hosted: in
`packages/backend/server/src/plugins/copilot/mcp/provider.ts`, `create_document`,
`update_document`, and `update_document_meta` are registered only when
`accessMode === READ_WRITE && (env.dev || env.namespaces.canary)`, and the same check blocks
issuing read-write credentials. Upstream tracks lifting this in
[toeverything/AFFiNE#15112](https://github.com/toeverything/AFFiNE/issues/15112) (open as of
2026-09). Option B avoids the limitation because it signs in as a normal user (email/password →
session cookie) and writes through the same WebSocket sync channel the web app uses.

**Pivot criterion:** if Option B's smoke test (step B6) can't create, read back, and edit a doc,
AFFiNE fails the "agent can read and write" requirement. Fall back per the
[appendix](#appendix-documentation-tool-comparison) (Outline first: its built-in MCP server
supports writes on self-hosted).

**Prerequisites for both options:**

- The workspace must be **server-backed**, not "local". Neither option can see browser-local
  workspaces.
- Claude Code runs on the MacBook, which reaches AFFiNE over the tailnet at
  `https://rainbow-flame.taila02055.ts.net:8444`. Check with
  `curl -sS -o /dev/null -w '%{http_code}\n' https://rainbow-flame.taila02055.ts.net:8444/`.
- Optional but recommended: a dedicated agent account. In the admin panel
  (`https://rainbow-flame.taila02055.ts.net:8444/admin` → Accounts), create a user such as
  `claude-agent@…` with a password, then invite it to the workspace (Workspace settings →
  Members). Docs it creates will show it in **Created by**, and you can revoke it without touching
  your own login. Using your own account works too for testing.

#### Option A: built-in MCP server (read-only)

1. **Turn on AI features server-wide.** The MCP endpoint is behind the `copilot.enabled` switch.
   It doesn't need a provider key; BYOK keys only power AI chat and semantic search. Use either:
   - Admin panel → Settings → AI → enable AI features, **or**
   - add this to `/home/mib/app/affine/config/config.json`, then run
     `docker compose restart affine`:
     ```json
     "copilot": { "enabled": true }
     ```
2. **Find the Integrations page.** It's a **workspace** setting, not an account setting. Open
   Settings (sidebar → workspace name menu → Settings). In the settings dialog's left column,
   under the **workspace** group (Preferences, Properties, Members, **Integrations**, Storage,
   …), pick **Integrations**.
   - The **MCP Server** card is hidden when the workspace is local. That's the usual reason it's
     missing.
   - **AI BYOK** appears here too, only for the workspace owner/admin. Skip it; MCP doesn't need
     it.
3. **Create a credential:** MCP Server → create credential → name it (`claude-code`), access
   mode **Read only** (read-write isn't offered on stable), and pick an expiry. Copy the
   `aff_mcp_v1…` token and the workspace ID from the JSON snippet it shows. The token is shown
   only once.
4. **Test the endpoint directly** from the Mac:
   ```bash
   WS=<workspace-id>; TOKEN=aff_mcp_v1...
   URL=https://rainbow-flame.taila02055.ts.net:8444/api/workspaces/$WS/mcp
   curl -sS "$URL" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   # expect: read_document and doc_search only
   ```
   A 403 `Copilot is disabled` means step 1 didn't take effect. `Authentication failed` means the
   token is wrong, expired, or belongs to a different workspace.
5. **Register it in Claude Code:**
   ```bash
   claude mcp add --scope user --transport http affine-builtin "$URL" \
     --header "Authorization: Bearer $TOKEN"
   claude mcp list   # affine-builtin … ✓ Connected
   ```
6. **Verify in a Claude Code session:** run `/mcp` (shows `affine-builtin` with 2 tools), then ask
   *"Use affine-builtin to search for <a word in one of your docs> and read the top result."*

`doc_search` depends on AFFiNE's search indexer, which the stock compose file disables
(`AFFINE_INDEXER_ENABLED=false`). If search comes back empty, `read_document` with a known doc
ID still works. The doc ID is the last path segment of the doc's URL.

Not recommended: setting `AFFINE_ENV=dev` on the server would unlock the write tools, but that
namespace also changes auth guards, sync, static-file serving, and more across the backend.

#### Option B: `affine-mcp-server` (read + write) — recommended

A community, MIT-licensed server, very active (v3.8.4 released 2026-09-29), ~290 GitHub stars,
with an end-to-end test suite that runs against a Docker AFFiNE stack. It runs on the Mac as a
local stdio process that Claude Code starts, so nothing new runs on rainbow-flame.

1. **Check Node.js** (20.18.1+ required): `node --version`
2. **Install**, pinned:
   ```bash
   npm i -g affine-mcp-server@3.8.4
   affine-mcp --version
   ```
3. **Log in.** This stores the URL, credentials, and default workspace in
   `~/.config/affine-mcp/config` (mode 600):
   ```bash
   affine-mcp login --save-credentials
   # URL:        https://rainbow-flame.taila02055.ts.net:8444
   # Method:     email/password (use the agent account, or your own for testing)
   # Workspace:  pick the server-backed workspace
   ```
   `--save-credentials` stores the password so the server can renew its session on its own.
   Without it, you'll have to re-run `login` whenever the session expires.
4. **Check it from the CLI:**
   ```bash
   affine-mcp status        # config resolves, sign-in works
   affine-mcp doctor        # connectivity diagnostics
   affine-mcp workspaces    # your workspace is listed and marked default
   ```
5. **Register it in Claude Code.** User scope makes it available in every project. The
   `authoring` profile exposes create/edit tools but leaves out destructive ones
   (`delete_doc`, `replace_doc_with_markdown`) and admin tools:
   ```bash
   claude mcp add --scope user -e AFFINE_TOOL_PROFILE=authoring affine -- affine-mcp
   claude mcp list   # affine … ✓ Connected
   ```
   Switch to `AFFINE_TOOL_PROFILE=full` later if you want the agent to delete or fully replace
   docs.
6. **Smoke test in a Claude Code session.** Run `/mcp` and confirm `affine` is connected with its
   tools listed. Then run these prompts in order:
   1. *"Using the affine MCP server, list my workspaces and the 5 most recently updated docs."*
   2. *"Create a doc titled `MCP smoke test` from this markdown: a heading, a bulleted list of 3
      items, and a fenced code block. Return its doc ID."* (`create_doc_from_markdown`)
   3. *"Read that doc back and export it as markdown."* (`read_doc`, `export_doc_markdown`)
   4. *"Append a section `## Update` with one paragraph, then change the first bullet's text to
      `edited by agent`."* (`append_markdown`, `update_block`)
   5. Open the doc in the browser **and** on the phone. Confirm the heading, list, code block,
      appended section, and edited bullet all render, and that edits you make there are visible
      when you ask Claude to read the doc again.
   6. Delete `MCP smoke test` by hand in the AFFiNE UI (the `authoring` profile can't delete).

   **Pass** = steps 2–5 all succeed. **Fail** = any write errors out or doesn't appear in the UI.
   First try `affine-mcp doctor`; if it still fails, pivot (see the pivot criterion above).

#### Other AFFiNE MCP options found (2026-09-30)

- [`emmabyte-engineering/affine-mcp`](https://github.com/emmabyte-engineering/affine-mcp)
  (`@emmabyte-eng/affine-mcp` on npm): self-hosted-focused, read/write, mermaid and table helpers.
  But it was created and last pushed on 2026-03-06, with 0 stars. Treat it as abandoned; only a
  fallback if Option B breaks.
- Forks of DAWNCR0W's server (HughArch, anpavlov, vadzhipov, werring, …): no advantage over
  upstream.
- Direct HTTP read, no MCP: `GET /workspace/<workspace-id>/<doc-id>` with
  `Accept: text/markdown` returns a doc as markdown for an authenticated caller. It's read-only
  and good for scripts.
- Built-in write tools (Option A with read-write): wait for upstream #15112. Re-check after each
  AFFiNE upgrade (§5d) by creating a credential and looking for a **Read & write** access mode.

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

## 6. Outline (trial alongside AFFiNE)

Outline runs next to AFFiNE so the two can be compared. Unlike AFFiNE, its **built-in MCP
server supports writes on self-hosted installs**. It's on by default and accepts a plain API key,
so no community server or workarounds are needed. Mobile is a PWA ("Add to Home Screen") rather
than a native app, per [Outline's mobile guide](https://docs.getoutline.com/s/guide/doc/mobile-Ez4bmY6VDD).

Versions checked (2026-09-30): Outline `v1.10.1`, Pocket ID `v2.16.0`.

### 6a. Why Pocket ID: Outline has no passwords

Outline has no local username/password login. The first account **must** come from an SSO
provider (Slack, Google, Microsoft, Discord, or generic OIDC). Email magic-link sign-in exists,
but only when SMTP is configured, and it only works for users of an already-created workspace.

[Pocket ID](https://github.com/pocket-id/pocket-id) is a small self-hosted OIDC provider (one
container, SQLite, ~9k stars) that signs you in with **passkeys**. Passkeys need HTTPS and a stable
host name, and the Tailscale cert provides both. Passkeys are stored in **1Password**, which
syncs them to the Mac and the phone. Pocket ID lives in its own directory so other services (Kaneo, a future
Docmost, …) can reuse it later.

The two stacks share a Docker network named `sso`. Outline's server-to-server OIDC calls (token
and userinfo) go straight to `http://pocket-id:1411` over that network. Only the browser-facing
login page uses the tailnet URL. This avoids relying on containers resolving MagicDNS names.

```bash
docker network create sso
```

### 6b. Pocket ID

1. **Directory and secret:**
   ```bash
   mkdir -p /home/mib/app/pocket-id/data && cd /home/mib/app/pocket-id
   openssl rand -base64 32   # ENCRYPTION_KEY
   ```
2. **`/home/mib/app/pocket-id/.env`:**
   ```env
   APP_URL=https://rainbow-flame.taila02055.ts.net:8446
   ENCRYPTION_KEY=<the value from step 1>
   TRUST_PROXY=true
   PUID=1000
   PGID=1000
   ```
   `APP_URL` must match the browser URL exactly. Passkeys are bound to this host name.
3. **`/home/mib/app/pocket-id/compose.yml`:**
   ```yaml
   services:
     pocket-id:
       image: ghcr.io/pocket-id/pocket-id:v2.16.0
       container_name: pocket-id
       restart: unless-stopped
       env_file: .env
       ports:
         - "127.0.0.1:1411:1411"
       volumes:
         - ./data:/app/data
       networks: [default, sso]
       healthcheck:
         test: ["CMD", "/app/pocket-id", "healthcheck"]
         interval: 1m30s
         timeout: 5s
         retries: 2
         start_period: 10s

   networks:
     sso:
       external: true
   ```
4. **Start it and expose it:**
   ```bash
   docker compose up -d
   docker compose ps   # healthy
   sudo tailscale serve --bg --https=8446 http://127.0.0.1:1411
   ```
5. **Create the admin user.** On the Mac, open
   `https://rainbow-flame.taila02055.ts.net:8446/setup`, create your user, and register a
   passkey. Save it to **1Password** when the browser extension offers. For the phone, turn on
   1Password as a passkey provider: iOS Settings → General → AutoFill & Passwords → 1Password
   (Android: Settings → Passwords & accounts → 1Password).
6. **Register Outline as an OIDC client:** Pocket ID admin → **OIDC Clients** → Add:
   - Name: `Outline`
   - Callback URL: `https://rainbow-flame.taila02055.ts.net:8445/auth/oidc.callback`
   - Save, then copy the **Client ID** and **Client secret**. The secret is shown once.
7. **Allow your user to use the client.** Pocket ID v2 creates new OIDC clients **restricted to
   user groups, with no groups selected**, so nobody can sign in. Outline's login then bounces
   to `…:8446/interaction/error?error=You+are+not+allowed+to+access+this+service`. Fix it with a
   group (recommended, since it also controls which accounts, such as an agent user, can reach
   Outline):
   - Pocket ID admin → **User Groups** → Add → name `outline-users` → add your user.
   - **OIDC Clients** → `Outline` → **Allowed user groups** → select `outline-users` → Save.

   Or open the `Outline` client and choose **Unrestrict** to let every Pocket ID user in.

Lost-passkey recovery: `docker compose exec pocket-id /app/pocket-id one-time-access-token <username>`
prints a one-time login link.

### 6c. Outline

1. **Directory and secrets:**
   ```bash
   mkdir -p /home/mib/app/outline && cd /home/mib/app/outline
   echo "SECRET_KEY=$(openssl rand -hex 32)"
   echo "UTILS_SECRET=$(openssl rand -hex 32)"
   echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
   ```
2. **`/home/mib/app/outline/.env`.** This is trimmed from the upstream `.env.sample`; anything not
   listed keeps its default:
   ```env
   OUTLINE_VERSION=1.10.1
   NODE_ENV=production
   URL=https://rainbow-flame.taila02055.ts.net:8445
   PORT=3000
   SECRET_KEY=<hex 32>
   UTILS_SECRET=<hex 32>
   DEFAULT_LANGUAGE=en_US

   POSTGRES_PASSWORD=<hex 24>   # used by both containers; DATABASE_URL is built from it in compose.yml
   PGSSLMODE=disable
   REDIS_URL=redis://redis:6379

   FILE_STORAGE=local
   FILE_STORAGE_LOCAL_ROOT_DIR=/var/lib/outline/data

   # TLS is terminated by tailscale serve; Outline itself only sees HTTP.
   FORCE_HTTPS=false

   # Pocket ID (browser goes to the tailnet URL; server-to-server calls use the sso network)
   OIDC_CLIENT_ID=<from 6b step 6>
   OIDC_CLIENT_SECRET=<from 6b step 6>
   OIDC_AUTH_URI=https://rainbow-flame.taila02055.ts.net:8446/authorize
   OIDC_TOKEN_URI=http://pocket-id:1411/api/oidc/token
   OIDC_USERINFO_URI=http://pocket-id:1411/api/oidc/userinfo
   OIDC_LOGOUT_URI=https://rainbow-flame.taila02055.ts.net:8446/api/oidc/end-session
   OIDC_USERNAME_CLAIM=preferred_username
   OIDC_DISPLAY_NAME=Pocket ID
   OIDC_SCOPES=openid profile email

   ENABLE_UPDATES=false
   LOG_LEVEL=info
   ```
3. **`/home/mib/app/outline/compose.yml`:**
   ```yaml
   services:
     outline:
       image: docker.getoutline.com/outlinewiki/outline:${OUTLINE_VERSION}
       env_file: .env
       environment:
         # Built from the same variable Postgres uses, so the two can't drift apart.
         DATABASE_URL: postgres://outline:${POSTGRES_PASSWORD}@postgres:5432/outline
       ports:
         - "127.0.0.1:3000:3000"
       volumes:
         - storage-data:/var/lib/outline/data
       depends_on:
         postgres:
           condition: service_healthy
         redis:
           condition: service_healthy
       networks: [default, sso]
       restart: unless-stopped

     redis:
       image: redis:7
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 10s
         timeout: 30s
         retries: 3
       restart: unless-stopped

     postgres:
       image: postgres:16
       environment:
         POSTGRES_USER: outline
         POSTGRES_DB: outline
         POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
       volumes:
         - database-data:/var/lib/postgresql/data
       healthcheck:
         test: ["CMD", "pg_isready", "-d", "outline", "-U", "outline"]
         interval: 30s
         timeout: 20s
         retries: 3
       restart: unless-stopped

   volumes:
     storage-data:
     database-data:

   networks:
     sso:
       external: true
   ```
4. **Start it and expose it.** Database migrations run automatically on first start:
   ```bash
   docker compose up -d
   docker compose logs -f outline   # wait for "Listening on http://localhost:3000", then Ctrl-C
   curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/   # 200
   docker compose exec outline wget -qO- http://pocket-id:1411/.well-known/openid-configuration | head -c 200   # sso network works
   sudo tailscale serve --bg --https=8445 http://127.0.0.1:3000
   ```
   **If `outline` keeps restarting with `password authentication failed for user "outline"`:**
   the password Outline sends doesn't match the one the Postgres data directory was **created**
   with. `POSTGRES_PASSWORD` only takes effect the first time the `database-data` volume is
   initialized. Changing `.env` afterwards (or a first `up` run before `.env` was filled in)
   leaves the old password in place.
   ```bash
   cd /home/mib/app/outline
   # 1. What will each container get? The two passwords must be identical.
   docker compose config | grep -E 'DATABASE_URL|POSTGRES_PASSWORD'
   # 2. Does Postgres accept the .env password? (127.0.0.1 forces a password check)
   PW=$(grep '^POSTGRES_PASSWORD=' .env | cut -d= -f2 | cut -d' ' -f1)
   docker compose exec postgres psql "postgresql://outline:$PW@127.0.0.1/outline" -c 'select 1'
   ```
   - If step 1 shows different values, fix `.env` or `compose.yml` and run `docker compose up -d`.
   - If step 2 fails, the volume holds an older password. On a fresh install with no data, wipe
     it and start over:
     ```bash
     docker compose down -v && docker compose up -d
     ```
     To keep existing data instead, set the password inside Postgres to match `.env` (the local
     socket doesn't ask for a password):
     ```bash
     docker compose exec postgres psql -U outline -d outline -c "ALTER USER outline PASSWORD '$PW';"
     docker compose restart outline
     ```
   - Keep secrets free of `@ : / ? #`, which would need URL-encoding inside `DATABASE_URL`.
     `openssl rand -hex` output is safe.
5. **First sign-in.** Open `https://rainbow-flame.taila02055.ts.net:8445/` → **Continue with
   Pocket ID** → sign in with the passkey. The first user to sign in creates the workspace and
   becomes its admin.
   - `You are not allowed to access this service` at Pocket ID: the client is group-restricted
     and your user isn't in an allowed group (6b step 7).
   - Redirect error at Pocket ID: the callback URL in 6b step 6 doesn't exactly match `URL` +
     `/auth/oidc.callback`.
   - Back at Outline with an auth error: check `docker compose logs outline`. If the token call
     failed, rerun the `wget` check from step 4.
6. **Set up the workspace:** create a collection per project (e.g. `sdlc-llm`, `Personal`).
   Collections are Outline's top level, with nested docs under them.
7. **Phone (PWA):** with the Tailscale app connected, open
   `https://rainbow-flame.taila02055.ts.net:8445` in **Safari** (iOS) or **Chrome** (Android) →
   sign in → Share → **Add to Home Screen** (Chrome: ⋮ → **Install app**). Launch it from the icon
   so it runs full-screen.
8. **Verify:** edit a doc in the PWA and watch it update live in the desktop browser, then the
   reverse. Outline uses real-time collaboration over WebSockets, which `tailscale serve`
   proxies.

### 6d. MCP (built-in, read + write)

Checked against the `v1.10.1` source: the `/mcp` endpoint accepts OAuth tokens **or** API keys.
It's gated by a workspace toggle (**Settings → Features → MCP**) that is **on by default**. It
exposes tools by the key's scopes, and a key with no scope restrictions gets everything. Document
tools include `list_documents`, `create_document`, `update_document`, `move_document`,
`delete_document`, and `restore_document`, plus collection, comment, attachment, template, user,
and fetch tools. Each call runs with the key owner's permissions.

1. **Confirm MCP is on:** Settings → **Features** → **MCP** is enabled.
2. **Create an API key:** Settings → **API & Apps** (API keys) → New → name it `claude-code`,
   leave scopes empty for full access (or restrict it later), and set an expiry. Copy the key.
   It's shown once.
   - Optional: create a dedicated agent user in Pocket ID (add it to `outline-users`), sign it
     into Outline once, give it
     access only to the collections the agent should touch, and create the key while signed in
     as that user.
3. **Test the endpoint directly** from the Mac:
   ```bash
   KEY=ol_api_...   # the key from step 2
   URL=https://rainbow-flame.taila02055.ts.net:8445/mcp
   curl -sS "$URL" -H "Authorization: Bearer $KEY" \
     -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | grep -o '"name":"[a-z_]*"' | sort -u
   # expect create_document, update_document, list_documents, …
   ```
   A 401 means the key is wrong or expired. A 404 means MCP is turned off in Settings → Features.
4. **Register it in Claude Code:**
   ```bash
   claude mcp add --scope user --transport http outline "$URL" \
     --header "Authorization: Bearer $KEY"
   claude mcp list   # outline … ✓ Connected
   ```
   Alternative: omit `--header` and run `/mcp` → **outline** → Authenticate to use Outline's
   OAuth flow in the browser instead of a stored key.
5. **Smoke test in a Claude Code session.** Run `/mcp` and confirm `outline` is connected with its
   tools listed. Then run these prompts in order:
   1. *"Using the outline MCP server, list my collections and the 5 most recently updated docs."*
   2. *"In the `sdlc-llm` collection, create a doc titled `MCP smoke test` with a heading, a
      bulleted list of 3 items, and a fenced code block. Return its ID/URL."* (`create_document`)
   3. *"Read that doc back."*
   4. *"Update it: append a section `## Update` with one paragraph and change the first bullet
      to `edited by agent`."* (`update_document`)
   5. *"Create a child doc `MCP smoke test – child` under it, then move it to the top level of the
      collection."* (`create_document`, `move_document`)
   6. Open both docs in the desktop browser **and** the PWA. Confirm the formatting and edits
      rendered, then edit something by hand and ask Claude to read it again.
   7. *"Delete both smoke-test docs."* (`delete_document`; Outline keeps them in Trash, so they can
      be restored.)

   **Pass** = steps 2–7 succeed with no workarounds. That's the bar AFFiNE only clears through the
   community server (§5c).

### 6e. Upgrading

Check the [release notes](https://github.com/outline/outline/releases) first, back up (see
[Moving to a new host](#moving-to-a-new-host), step 2), then bump `OUTLINE_VERSION` in `.env`
and run `docker compose pull && docker compose up -d`. Migrations run on start. Pocket ID works
the same way: bump the image tag in its `compose.yml`.

### 6f. Removing whichever tool loses

```bash
# Outline loses:
cd /home/mib/app/outline && docker compose down -v && sudo tailscale serve --https=8445 off
# Pocket ID too, if nothing else uses it:
cd /home/mib/app/pocket-id && docker compose down && sudo tailscale serve --https=8446 off
docker network rm sso
claude mcp remove outline
# AFFiNE loses:
cd /home/mib/app/affine && docker compose down && sudo tailscale serve --https=8444 off
claude mcp remove affine; claude mcp remove affine-builtin 2>/dev/null
```

Delete the loser's directory under `/home/mib/app/` and its rows in the migration inventory.

---

## 7. Final serve config and checks

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
https://rainbow-flame.taila02055.ts.net:8445 (tailnet only)
|-- / proxy http://127.0.0.1:3000
https://rainbow-flame.taila02055.ts.net:8446 (tailnet only)
|-- / proxy http://127.0.0.1:1411
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
| Outline | `/home/mib/app/outline` | Docker volumes `outline_database-data` (Postgres), `outline_storage-data` (attachments) | `SECRET_KEY`, `UTILS_SECRET`, `POSTGRES_PASSWORD`, `OIDC_CLIENT_SECRET` | `URL`, `OIDC_AUTH_URI`, `OIDC_LOGOUT_URI`; external `sso` network | `:8445 → 127.0.0.1:3000` |
| Pocket ID | `/home/mib/app/pocket-id` | `./data` (SQLite DB + keys) | `ENCRYPTION_KEY` | `APP_URL`; each OIDC client's callback URL; **passkeys are bound to the host name**, so a new name means re-registering them (use `one-time-access-token`) | `:8446 → 127.0.0.1:1411` |
| Outline MCP (on the Mac) | Claude Code user MCP config (`claude mcp list`) | none | Outline API key (in the Claude Code config) | endpoint URL: `claude mcp remove outline` and re-add | n/a |
| AFFiNE MCP (on the Mac, not the server) | `~/.config/affine-mcp/config`; Claude Code user MCP config (`claude mcp list`) | none | agent account password (in the affine-mcp config); built-in `aff_mcp_v1…` token if Option A is used | AFFiNE URL: re-run `affine-mcp login`; built-in endpoint URL: `claude mcp remove affine-builtin` and re-add | n/a |

### Moving to a new host

1. On the old host, run `docker compose down` in each `/home/mib/app/*` directory.
2. Before the `down`, dump every Postgres database:
   - Kaneo: `docker compose exec postgres pg_dump -U kaneo kaneo > kaneo.sql`
   - AFFiNE: `docker compose exec postgres pg_dump -U affine affine > affine.sql`
   - Outline: `docker compose exec postgres pg_dump -U outline outline > outline.sql`. Also copy
     the `outline_storage-data` volume (e.g.
     `docker run --rm -v outline_storage-data:/d -v "$PWD":/b alpine tar czf /b/outline-storage.tgz -C /d .`).
   - SparkyFitness: do the same for its Postgres.

   Bind-mounted data dirs copy fine when the stack is stopped, but a dump is the version-safe
   backup.
3. Copy all of `/home/mib/app/` with `rsync -aHAX`, which preserves ownership for bind mounts.
4. Restore the dumps into the new Postgres containers.
5. Update the host-specific URLs in the table above, run `docker compose up -d`, and re-run the
   `tailscale serve` commands.
6. If the host name changed, update AFFiNE's `externalUrl`, re-add the server in the AFFiNE
   mobile app, and on the Mac re-run `affine-mcp login` (plus re-add `affine-builtin` if used).
7. Run `docker network create sso` on the new host before starting Pocket ID and Outline. If
   the host name changed, update Pocket ID's `APP_URL`, Outline's OIDC client callback URL, and
   Outline's `URL`/`OIDC_*` values, then re-register passkeys.
8. Remove the old host's serve config with `sudo tailscale serve reset`.

---

## Appendix: documentation tool comparison

**Decision (2026-09): AFFiNE.** Obsidian was tried and rejected. Its "self-hosted" mode is the
desktop app streamed into a browser tab (plus a separate CouchDB for LiveSync), and the setup
felt clumsy and fragile. AFFiNE won because it has a native mobile app that connects to a
self-hosted server, plus a Miro-style canvas.

**Now trialling Outline side by side (§6)** because its built-in MCP server supports writes on
self-hosted installs with no workarounds, and its PWA may be good enough on mobile.

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
| Native app for your own server | ✅ iOS/Android | ❌ (official PWA instead) | ❌ | ❌ | ✅ | ❌ | ✅ but syncs via LiveSync, not the server |
| LLM / MCP access | 🟡 built-in is read-only on stable self-hosted; read/write via the community `affine-mcp-server` (§5c) | ✅ built-in `/mcp`, read + write on self-hosted, API key or OAuth, on by default (§6d) | 🟡 built-in one needs a paid licence; community servers use the free API | 🟡 community server over a solid REST API | 🟡 community | 🟡 API + community | 🟡 via a community plugin, or just read the files |
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
