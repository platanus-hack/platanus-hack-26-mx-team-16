# Remediation snippets — stack agnostic

Paste-ready fixes for every FAIL found in the audit. Pick the variant that matches the project's base image and package manager. Adapt names and versions to the project.

---

## CIS 4.1 — Non-root user

### Debian / Ubuntu base
```dockerfile
RUN groupadd --system --gid 1001 app \
 && useradd  --system --uid 1001 --gid app --home /home/app --create-home --shell /usr/sbin/nologin app
USER app:app
WORKDIR /home/app
```

### Alpine base
```dockerfile
RUN addgroup -S -g 1001 app && adduser -S -u 1001 -G app -h /home/app -s /sbin/nologin app
USER app:app
```

### Red Hat / Fedora / Rocky / UBI
```dockerfile
RUN groupadd -r -g 1001 app && useradd -r -u 1001 -g app -d /home/app -s /sbin/nologin -m app
USER app:app
```

### Already-shipped non-root user (use it directly)
- `node:*` images ship `node` (uid 1000) → `USER node`
- `bitnami/*` images often ship uid 1001 → `USER 1001`
- `nginxinc/nginx-unprivileged` listens on 8080 as `nginx` → `USER nginx`

### Distroless final stage
```dockerfile
FROM gcr.io/distroless/nodejs20-debian12:nonroot
# distroless :nonroot variants run as uid 65532 by default — no extra USER needed.
```

> Pick an explicit UID/GID (1000+, often 1001) so host-mounted volumes have predictable ownership across rebuilds. Avoid `USER root` after the final switch.

---

## CIS 4.2 — Trusted base image

Pin by digest, not just tag, and prefer trusted sources:
```dockerfile
# Docker Official Image, pinned by digest:
FROM python:3.12-slim-bookworm@sha256:<digest>
```
Sources, in order of preference:
1. Internal mirror you control (`registry.company.com/library/...`)
2. Docker Official Images
3. Verified Publisher
4. Distroless (`gcr.io/distroless/...`)
5. Anything else → MANUAL (justify with a comment in the report)

---

## CIS 4.3 — Minimal packages

### apt (Debian/Ubuntu)
```dockerfile
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
 && rm -rf /var/lib/apt/lists/*
```

### apk (Alpine)
```dockerfile
RUN apk add --no-cache ca-certificates curl
```

### dnf / microdnf (Fedora / UBI)
```dockerfile
RUN microdnf install -y --nodocs --setopt=install_weak_deps=0 ca-certificates curl \
 && microdnf clean all
```

Prefer **distroless** or **alpine** over a full distro when the runtime allows. Switch base image families only with user consent.

---

## CIS 4.4 — Scan + rebuild in CI

### GitHub Actions — Trivy
```yaml
- name: Scan image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
    severity: HIGH,CRITICAL
    exit-code: '1'
    ignore-unfixed: true
```

### GitHub Actions — Docker Scout
```yaml
- name: Scan image
  uses: docker/scout-action@v1
  with:
    command: cves
    image: ghcr.io/${{ github.repository }}:${{ github.sha }}
    only-severities: critical,high
    exit-code: true
```

### GitLab CI — Trivy
```yaml
container_scan:
  image: aquasec/trivy:latest
  script:
    - trivy image --severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed $IMAGE_TAG
```

### Local one-shot
```bash
docker scout cves --exit-code 1 --only-severity high,critical <image>
# or
trivy image --severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed <image>
```

---

## CIS 4.6 — HEALTHCHECK

### Web service with HTTP health endpoint
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl --fail --silent http://127.0.0.1:${PORT:-8080}/health || exit 1
```
Replace `curl` with `wget --quiet --spider` on busybox/alpine where curl isn't installed.

### TCP-only service
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD nc -z 127.0.0.1 ${PORT} || exit 1
```

### CLI/worker (no HTTP)
```dockerfile
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
  CMD pgrep -f "my-worker" >/dev/null || exit 1
```

### In compose (overrides image's HEALTHCHECK)
```yaml
healthcheck:
  test: ["CMD", "curl", "--fail", "--silent", "http://127.0.0.1:8080/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

### Distroless (no shell, no curl)
Embed a tiny healthcheck binary or use the language runtime:
```dockerfile
HEALTHCHECK CMD ["/app/healthcheck"]
# or for Go services:
HEALTHCHECK CMD ["/app", "healthcheck"]
```

---

## CIS 4.7 — Update + install in one layer

### apt
**Bad:**
```dockerfile
RUN apt-get update
RUN apt-get install -y curl
```
**Good:**
```dockerfile
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl=7.88.* \
 && rm -rf /var/lib/apt/lists/*
```

### apk
```dockerfile
RUN apk add --no-cache curl=~8.7
```

### dnf
```dockerfile
RUN dnf install -y --setopt=install_weak_deps=0 curl-8.6.0-* \
 && dnf clean all
```

---

## CIS 4.9 — COPY over ADD

**Bad:**
```dockerfile
ADD https://example.com/x.tar.gz /opt/
ADD app.tar.gz /opt/
```
**Good (remote file with checksum):**
```dockerfile
RUN curl -fsSLO https://example.com/x.tar.gz \
 && echo "<sha256>  x.tar.gz" | sha256sum --check \
 && tar -xzf x.tar.gz -C /opt && rm x.tar.gz
```
**Good (local files):**
```dockerfile
COPY app/ /opt/app/
```

---

## CIS 4.10 — BuildKit secrets

### Generic
```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=mysecret,target=/run/secrets/mysecret \
    do-stuff-with $(cat /run/secrets/mysecret)
```
```bash
DOCKER_BUILDKIT=1 docker build --secret id=mysecret,src=$HOME/.mysecret -t myimage .
```

### npm / pnpm / yarn (private registry token)
```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci --omit=dev
```

### pip (private index)
```dockerfile
RUN --mount=type=secret,id=pip_conf,target=/etc/pip.conf \
    pip install --no-cache-dir -r requirements.txt
```

### Maven (settings.xml)
```dockerfile
RUN --mount=type=secret,id=mvn_settings,target=/root/.m2/settings.xml \
    mvn -B -DskipTests package
```

### Go (GOPROXY auth)
```dockerfile
RUN --mount=type=secret,id=netrc,target=/root/.netrc go mod download
```

### Cargo (private registry)
```dockerfile
RUN --mount=type=secret,id=cargo_credentials,target=/root/.cargo/credentials.toml \
    cargo build --release
```

**Never** `COPY .npmrc`, `ENV NPM_TOKEN=…`, `ARG GITHUB_TOKEN=…`, or `COPY id_rsa`. All of those leak into layers.

---

## CIS 4.11 — Verified packages

### Add a signed apt repo
```dockerfile
RUN curl -fsSL https://download.docker.com/linux/debian/gpg \
      | gpg --dearmor -o /usr/share/keyrings/docker.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" \
      > /etc/apt/sources.list.d/docker.list \
 && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli \
 && rm -rf /var/lib/apt/lists/*
```

### Verify a downloaded binary
```dockerfile
ARG TOOL_VERSION=1.2.3
ARG TOOL_SHA256=<expected_sha256>
RUN curl -fsSLO https://example.com/tool-${TOOL_VERSION}.tar.gz \
 && echo "${TOOL_SHA256}  tool-${TOOL_VERSION}.tar.gz" | sha256sum --check \
 && tar -xzf tool-${TOOL_VERSION}.tar.gz -C /usr/local/bin \
 && rm tool-${TOOL_VERSION}.tar.gz
```

### Language ecosystems with built-in verification
- npm: `npm ci` against a committed `package-lock.json` (integrity hashes baked in).
- pip: `pip install --require-hashes -r requirements.txt`.
- Cargo: `cargo` verifies registry checksums automatically.
- Go: `go mod verify` and `GOFLAGS=-mod=readonly`.

---

## CIS 5.7 — No sshd

Remove:
```dockerfile
# BAD
RUN apt-get install -y openssh-server
```
For interactive access, use `docker exec -it <id> sh` (or `kubectl exec`).

---

## CIS 5.9 — Only necessary ports

### Dockerfile
```dockerfile
EXPOSE 8080
```
List only the real app port.

### Compose — preferred bindings
```yaml
ports:
  - "127.0.0.1:8080:8080"   # loopback-only when fronted by a reverse proxy
```
Never `docker run -P` / `--publish-all` in scripts or Makefiles.

---

## CIS 5.28 — Pin image versions by digest

```dockerfile
FROM python:3.12-slim-bookworm@sha256:<digest>
```
```yaml
services:
  api:
    image: ghcr.io/org/repo@sha256:<digest>
```
Let Renovate / Dependabot bump digests via PR.

---

# Runtime hardening — compose snippets

## B1 — read_only + tmpfs

```yaml
services:
  api:
    read_only: true
    tmpfs:
      - /tmp
      - /run
```

## B2 — drop all capabilities

```yaml
services:
  api:
    cap_drop: ["ALL"]
    cap_add:
      - NET_BIND_SERVICE   # only if listening on a port <1024
```

## B3 — no-new-privileges

```yaml
services:
  api:
    security_opt:
      - "no-new-privileges:true"
```

## B4 — non-root user override

```yaml
services:
  api:
    user: "1001:1001"
```

## B5 — read-only bind mounts

```yaml
volumes:
  - ./config:/app/config:ro
```

## B6 — resource limits

Compose v3 / swarm:
```yaml
services:
  api:
    deploy:
      resources:
        limits:       { cpus: "1.0", memory: 512M }
        reservations: { cpus: "0.25", memory: 128M }
```
Compose v2 / single-node:
```yaml
services:
  api:
    mem_limit: 512m
    cpus: 1.0
    pids_limit: 200
```

## B7 — never `privileged: true`

If you find `privileged: true` outside a dedicated docker-in-docker / build runner, mark FAIL. The minimum viable replacement is targeted capabilities (`cap_add: [SYS_ADMIN]` etc.) with `security_opt`.

## B8 — internal networks

```yaml
networks:
  internal: { internal: true }
  edge: {}

services:
  api:
    networks: [internal]
  nginx:
    networks: [internal, edge]
    ports: ["443:443"]
```

## B9 — secrets block

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt

services:
  api:
    secrets: [db_password]
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password
```

## B10 — bounded logging

```yaml
services:
  api:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
```

## B11 — restart policy

```yaml
services:
  api:
    restart: unless-stopped     # or: on-failure[:max-retries]
```
Pick `unless-stopped` for long-running services, `on-failure` for jobs that may legitimately exit. Avoid `always` — it restarts even after a successful `docker stop`, which masks shutdown bugs.

## B12 — PID 1 init reaper

```yaml
services:
  api:
    init: true
```
Equivalent of `docker run --init`. Adds a tiny init (`tini` / `docker-init`) as PID 1 so signals propagate (`SIGTERM`/`SIGINT`) and zombie processes are reaped. Essential for any language runtime that spawns subprocesses (Node, Python with multiprocessing, shell wrappers).

If you bake `tini` into the image instead:
```dockerfile
RUN apk add --no-cache tini   # or: apt-get install -y --no-install-recommends tini
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["my-app"]
```

---

# Full hardened skeleton (multi-stage, language-agnostic shape)

```dockerfile
# syntax=docker/dockerfile:1.7

############################
# 1. Builder stage
############################
FROM <build-base>@sha256:<digest> AS builder
WORKDIR /src
COPY <lockfiles> ./
RUN --mount=type=cache,target=<lang-cache-dir> \
    --mount=type=secret,id=<registry-creds> \
    <install-deps>
COPY . .
RUN <build-output>

############################
# 2. Runtime stage
############################
FROM <runtime-base>@sha256:<digest> AS runtime

ENV LANG=C.UTF-8 \
    TZ=UTC

# Non-root user (skip if base already ships one)
RUN groupadd --system --gid 1001 app \
 && useradd  --system --uid 1001 --gid app --home /home/app --create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=app:app /src/<artifacts> ./

USER app:app
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl --fail --silent http://127.0.0.1:8080/health || exit 1

ENTRYPOINT ["<binary-or-runner>"]
CMD ["<args>"]
```

```yaml
# Hardened compose service block (works for any language)
services:
  api:
    image: ghcr.io/org/repo@sha256:<digest>
    user: "1001:1001"
    read_only: true
    tmpfs: ["/tmp", "/run"]
    cap_drop: ["ALL"]
    security_opt: ["no-new-privileges:true"]
    networks: [internal]
    ports: ["127.0.0.1:8080:8080"]
    secrets: [db_password]
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password
    healthcheck:
      test: ["CMD", "curl", "--fail", "--silent", "http://127.0.0.1:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "5" }
    deploy:
      resources:
        limits: { cpus: "1.0", memory: 512M }

networks:
  internal: { internal: true }

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

# Language-specific tips (notes for adapting the skeleton)

- **Python.** Use `python:*-slim` or distroless (`gcr.io/distroless/python3-debian12`). Set `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`. Install with `pip install --require-hashes` or `uv sync --frozen`.
- **Node.** Use `node:*-alpine` or distroless (`gcr.io/distroless/nodejs20-debian12:nonroot`). Builder stage runs `npm ci` (or `pnpm install --frozen-lockfile`, `yarn install --immutable`); runtime stage copies only `dist/` + `node_modules` + `package.json`. Drop dev deps via `npm prune --production`.
- **Go.** Build with `CGO_ENABLED=0 go build -ldflags="-s -w" -trimpath`. Final stage = `gcr.io/distroless/static-debian12:nonroot` or `scratch`. No package manager needed.
- **Java.** Use a JRE-only runtime (`eclipse-temurin:21-jre-alpine`) or distroless (`gcr.io/distroless/java21-debian12:nonroot`). Multi-stage with `mvn -B package` or `gradle assemble` in builder.
- **.NET.** Use `mcr.microsoft.com/dotnet/aspnet:8.0-alpine` or distroless variants. Builder stage uses `dotnet/sdk`. `dotnet publish -c Release -o /app /p:PublishTrimmed=true` shrinks attack surface.
- **Ruby.** Use `ruby:*-alpine` with `bundle install --without development test --jobs 4 --retry 3 --deployment`. For Rails, run `assets:precompile` in builder.
- **PHP.** Use `php:*-fpm-alpine`. Run `composer install --no-dev --prefer-dist --optimize-autoloader` with `--mount=type=secret` for `auth.json`.
- **Rust.** Build in `rust:*-alpine`, copy the static binary to `gcr.io/distroless/cc-debian12:nonroot` or `scratch`.

In all cases the **shape** of the Dockerfile is identical: build stage → strip → runtime stage with non-root user, HEALTHCHECK, pinned digest, minimal packages, BuildKit secrets, COPY (never ADD), no sshd, only necessary ports.
