# Self-hosted services on `rainbow-flame`

How **SparkyFitness**, **Kaneo**, and **Outline** (with **Pocket ID** for sign-in) are installed
and served on `rainbow-flame`, and where each one keeps its config and data so they can be moved
to another host (see [Migration inventory](#migration-inventory)).

| | |
|---|---|
| Host | `rainbow-flame` (Ubuntu 24.04) |
| Tailnet name | `rainbow-flame.taila02055.ts.net` |
| Tailnet IP | `100.105.75.3` |
| Runtime | Docker + Docker Compose plugin |
| Ingress | `tailscale serve` (HTTPS, tailnet-only, no Funnel) |

---

## 1. Ingress design

**Each service gets its own HTTPS port on the same MagicDNS name.** `tailscale serve` accepts any
HTTPS port (only Funnel is limited to 443/8443/10000), and the Tailscale-issued cert covers every
port on the host name. Port 443 is unused.

Path-based routing (`tailscale serve --set-path=/kaneo …`) doesn't work here. Serve strips the
prefix before proxying, but these single-page apps assume they run at `/` and have no base-path
setting. Their HTML then requests `/assets/…`, which no serve handler matches, and the result is
a blank page with "disallowed MIME type (text/plain)" errors in the console.

Every container publishes its port on **loopback only** (`127.0.0.1:<port>`). `tailscale serve`
is the only way in, which always gives you HTTPS. It also avoids a clash where the same port
number is both served by Tailscale and bound by Docker on all interfaces (SparkyFitness uses
3004 for both).

### Port plan

| Service | Local (loopback) | Tailnet URL |
|---|---|---|
| SparkyFitness | `127.0.0.1:3004` | `https://rainbow-flame.taila02055.ts.net:3004/` |
| Kaneo | `127.0.0.1:5173` | `https://rainbow-flame.taila02055.ts.net:8443/` |
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

# Common directory for all service configs + data (makes migration a single tree)
mkdir -p /home/mib/app
```

---

## 3. SparkyFitness

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
3. **Start (or recreate) the containers:**
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
   and log in. The mobile app's server URL is `https://rainbow-flame.taila02055.ts.net:3004`.

#### Troubleshooting: `Authentication Failed: Invalid Origin`

The console shows `403 {"message":"Invalid origin","code":"INVALID_ORIGIN"}`. The server rejected
the login because the request's `Origin` header isn't in its trusted-origins list. That list is
`SPARKY_FITNESS_FRONTEND_URL` plus any entries in `SPARKY_FITNESS_EXTRA_TRUSTED_ORIGINS`. It
happens whenever you reach the app at a URL other than the configured one, or after that URL
changes (e.g. a host move).

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

Fresh install (e.g. on a new host): download the compose file with
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

If port 5173 is already taken, find the holder with `docker ps` before step 4.

---

## 5. Outline (docs, notes)

Outline is the self-hosted documentation tool. Its **built-in MCP server reads and writes docs on
self-hosted installs**. It's on by default and accepts a plain API key. Mobile is a PWA ("Add to Home Screen") rather
than a native app, per [Outline's mobile guide](https://docs.getoutline.com/s/guide/doc/mobile-Ez4bmY6VDD).

Versions checked (2026-09-30): Outline `v1.10.1`, Pocket ID `v2.16.0`.

### 5a. Why Pocket ID: Outline has no passwords

Outline has no local username/password login. The first account **must** come from an SSO
provider (Slack, Google, Microsoft, Discord, or generic OIDC). Email magic-link sign-in exists,
but only when SMTP is configured, and it only works for users of an already-created workspace.

[Pocket ID](https://github.com/pocket-id/pocket-id) is a small self-hosted OIDC provider (one
container, SQLite, ~9k stars) that signs you in with **passkeys**. Passkeys need HTTPS and a stable
host name, and the Tailscale cert provides both. Passkeys are stored in **1Password**, which
syncs them to the Mac and the phone. Pocket ID lives in its own directory so other services (e.g.
Kaneo) can reuse it.

The two stacks share a Docker network named `sso`. Outline's server-to-server OIDC calls (token
and userinfo) go straight to `http://pocket-id:1411` over that network. Only the browser-facing
login page uses the tailnet URL. This avoids relying on containers resolving MagicDNS names.

```bash
docker network create sso
```

### 5b. Pocket ID

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

### 5c. Outline

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
   OIDC_CLIENT_ID=<from 5b step 6>
   OIDC_CLIENT_SECRET=<from 5b step 6>
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
     and your user isn't in an allowed group (5b step 7).
   - Redirect error at Pocket ID: the callback URL in 5b step 6 doesn't exactly match `URL` +
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

### 5d. MCP (built-in, read + write)

Checked against the `v1.10.1` source: the `/mcp` endpoint accepts OAuth tokens **or** API keys.
It's gated by a workspace toggle (**Preferences → AI → MCP server**) that is **on by default**. It
exposes tools by the key's scopes, and a key with no scope restrictions gets everything. Document
tools include `list_documents`, `create_document`, `update_document`, `move_document`,
`delete_document`, and `restore_document`, plus collection, comment, attachment, template, user,
and fetch tools. Each call runs with the key owner's permissions.

1. **Confirm MCP is on:** Preferences → **AI** → **MCP server** is enabled.
2. **Create an API key:** Preferences → **API & Apps** (API keys) → New → name it `claude-code`,
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
   A 401 means the key is wrong or expired. A 404 means MCP is turned off (Preferences → AI → MCP server).
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

   **Pass** = steps 2–7 all succeed.
6. **Stop the per-call approval prompts.** Claude Code asks before every MCP tool call until the
   tool is allowed. To allow every tool on the `outline` server, add a permission rule to your
   **user** settings, `~/.claude/settings.json`, which matches the user-scoped server and applies
   in every project. Merge it into the existing `permissions` block if there is one:
   ```json
   {
     "permissions": {
       "allow": ["mcp__outline"],
       "ask": ["mcp__outline__delete_document"]
     }
   }
   ```
   - `mcp__outline` (the server name, with no tool suffix) matches **all** of that server's
     tools.
   - The optional `ask` rule keeps a confirmation on deletes. `ask` takes precedence over
     `allow`. Drop it if you want deletes to go through without a prompt too.
   - The same rules can be added interactively with `/permissions` → Allow → `mcp__outline`.
     Answering "Yes, and don't ask again" in a prompt only allows that one tool.
   - Restart Claude Code (or start a new session), then check `/permissions` lists the rule.

### 5e. Upgrading

Check the [release notes](https://github.com/outline/outline/releases) first, back up (see
[Moving to a new host](#moving-to-a-new-host), step 2), then bump `OUTLINE_VERSION` in `.env`
and run `docker compose pull && docker compose up -d`. Migrations run on start. Pocket ID works
the same way: bump the image tag in its `compose.yml`.

### 5f. Removing Outline

```bash
cd /home/mib/app/outline && docker compose down -v && sudo tailscale serve --https=8445 off
# Pocket ID too, if nothing else uses it:
cd /home/mib/app/pocket-id && docker compose down && sudo tailscale serve --https=8446 off
docker network rm sso
claude mcp remove outline --scope user   # and drop the mcp__outline rules from ~/.claude/settings.json
```

Then delete the directories under `/home/mib/app/` and their rows in the migration inventory.

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
| Outline | `/home/mib/app/outline` | Docker volumes `outline_database-data` (Postgres), `outline_storage-data` (attachments) | `SECRET_KEY`, `UTILS_SECRET`, `POSTGRES_PASSWORD`, `OIDC_CLIENT_SECRET` | `URL`, `OIDC_AUTH_URI`, `OIDC_LOGOUT_URI`; external `sso` network | `:8445 → 127.0.0.1:3000` |
| Pocket ID | `/home/mib/app/pocket-id` | `./data` (SQLite DB + keys) | `ENCRYPTION_KEY` | `APP_URL`; each OIDC client's callback URL; **passkeys are bound to the host name**, so a new name means re-registering them (use `one-time-access-token`) | `:8446 → 127.0.0.1:1411` |
| Outline MCP (on the Mac) | Claude Code user MCP config (`claude mcp list`); permission rules in `~/.claude/settings.json` | none | Outline API key (in the Claude Code config) | endpoint URL: `claude mcp remove outline` and re-add | n/a |

### Moving to a new host

1. On the old host, run `docker compose down` in each `/home/mib/app/*` directory.
2. Before the `down`, dump every Postgres database:
   - Kaneo: `docker compose exec postgres pg_dump -U kaneo kaneo > kaneo.sql`
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
6. If the host name changed, re-add the Outline MCP server on the Mac
   (`claude mcp remove outline --scope user`, then §5d step 4) and reinstall the PWA on the phone.
7. Run `docker network create sso` on the new host before starting Pocket ID and Outline. If
   the host name changed, update Pocket ID's `APP_URL`, Outline's OIDC client callback URL, and
   Outline's `URL`/`OIDC_*` values, then re-register passkeys.
8. Remove the old host's serve config with `sudo tailscale serve reset`.
