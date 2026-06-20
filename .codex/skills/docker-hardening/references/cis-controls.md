# CIS Docker Benchmark — Level 1

Twelve controls audited by this skill. Source: CIS Docker Benchmark Level 1 (and the internal hardening checklist that derives from it). Stack-agnostic.

---

## Chapter 4 — Container images and build-file configuration

### 4.1 — Ensure a non-root user is created for the container

**Description.** Containers must run as a non-root user.

**Risk.** Running as root inside a container means a container escape gives root on the host (or in the user namespace). Use the `USER` directive in the Dockerfile, or `gosu` / `su-exec` / `tini` in `CMD`/`ENTRYPOINT` when initialization requires root before dropping.

**Audit.**
```bash
docker ps --quiet | xargs --max-args=1 -I{} docker exec {} cat /proc/1/status \
  | grep '^Uid:' | awk '{print $3}'
```
Returns the effective UID of each container. `0` = running as root.

**Remediation.** Add to the Dockerfile:
```dockerfile
RUN useradd --system --uid 1001 --gid 1001 --shell /usr/sbin/nologin app
USER app
```
If `USER` is impractical, use a script in `CMD`/`ENTRYPOINT` that switches user before exec.

---

### 4.2 — Ensure containers use only trusted base images

**Description.** Use images built from scratch, an established and trusted base image, or a Docker Official / Verified Publisher / internal-mirror image. Pull only over secure channels.

**Risk.** Public registries can host vulnerable or malicious images.

**Audit.**
```bash
docker images
docker history <image-name>
```
Review provenance and contents per your security policy.

**Remediation.** Configure Docker Content Trust, review `docker history` before deploys, scan images regularly, and pin by digest (see 5.28).

---

### 4.3 — Ensure unnecessary packages are not installed in the container

**Description.** Keep the container footprint minimal.

**Risk.** Extra software = larger attack surface and more CVE exposure.

**Audit.**
```bash
docker ps --quiet
docker exec $INSTANCE_ID rpm -qa     # or: apt list --installed / apk info / dnf list installed
```

**Remediation.** Use minimal base images (Alpine, distroless, slim). Install with `--no-install-recommends` (apt) / `--no-cache` (apk). Prefer multi-stage builds where the final stage is `scratch` or `distroless` when the runtime allows.

---

### 4.4 — Ensure images are scanned and rebuilt to include security patches

**Description.** Scan images frequently for vulnerabilities and rebuild to include patches.

**Risk.** Unpatched vulnerabilities can be exploited. Unsupported versions stop receiving fixes.

**Audit.** Run a vulnerability scanner (Docker Scout, Trivy, Grype, Snyk) against every image in the registry. Verify package versions inside running containers.

**Remediation.** Rebuild periodically using the latest base image and restart containers from the new images. Integrate scanning into CI with `--exit-code 1` so HIGH/CRITICAL findings block the pipeline.

---

### 4.6 — Ensure HEALTHCHECK instructions have been added

**Description.** Every image should declare a health check.

**Risk.** Without HEALTHCHECK, the Docker engine cannot detect unhealthy containers and orchestrators cannot trigger restarts.

**Audit.**
```bash
docker inspect --format='{{ .Config.Healthcheck }}' <image>
```

**Remediation.** Add `HEALTHCHECK CMD …` in the Dockerfile, or `healthcheck:` in the compose service.

---

### 4.7 — Ensure update instructions are not used alone in Dockerfiles

**Description.** Don't put `apt-get update` / `yum update` / `apk update` on its own line.

**Risk.** The update layer gets cached and subsequent builds reuse the stale cache, silently skipping security updates.

**Audit.**
```bash
docker images
docker history <image-id>
```
Look for an `update` step that's not chained to `install`.

**Remediation.** Combine `update` and `install` in a single `RUN` with `&&`, pin package versions, or build with `--no-cache`.

---

### 4.9 — Use COPY instead of ADD in Dockerfiles

**Description.** Prefer `COPY`. `ADD` is acceptable only for extracting a local tar archive — and should carry a comment justifying it.

**Risk.** `ADD` can fetch remote URLs and auto-extract archives. Both expand the attack surface (no integrity check on remote content, decompression bugs).

**Audit.**
```bash
docker history <image-id>
```
Search for `ADD` instructions.

**Remediation.** Replace `ADD` with `COPY`. For remote artifacts, use `RUN curl -fsSLO … && sha256sum --check …`.

---

### 4.10 — Ensure secrets are not stored in Dockerfiles

**Description.** No tokens, passwords, private keys in `ENV` / `ARG` / `COPY` of any Dockerfile.

**Risk.** Image layers are visible to anyone who pulls the image (`docker history`, registry blobs).

**Audit.**
```bash
docker history <image-id>
```
Inspect `ENV` / `ARG` values and copied files.

**Remediation.** Use BuildKit secrets:
```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=token,target=/run/secrets/token \
    install-using $(cat /run/secrets/token)
```
Build with `docker build --secret id=token,src=$HOME/.token …`. Pass runtime secrets via environment or a secrets manager.

---

### 4.11 — Ensure only verified packages are installed

**Description.** Verify package authenticity (GPG, checksums, signed repos) before installing.

**Risk.** Untrusted packages may be malicious or vulnerable.

**Audit.**
```bash
docker history <image-id>
```
Confirm signed repos or checksum verification.

**Remediation.** Use signed package repositories. For external binaries, `sha256sum --check` or `gpg --verify` before installing.

---

## Chapter 5 — Container runtime configuration

### 5.7 — Ensure sshd is not running inside containers

**Description.** Don't run `sshd` inside the container.

**Risk.** Adds complexity around key management, patch management, and access policies. `docker exec` (or `kubectl exec`) covers the legitimate need for an in-container shell.

**Audit.**
```bash
docker ps --quiet
docker exec <container-id> ps -el
```
Ensure no `sshd` process.

**Remediation.** Uninstall `openssh-server` from the image. Use `docker exec -it <id> sh` for interactive access.

---

### 5.9 — Ensure only necessary ports are open on the container

**Description.** Both Dockerfile (`EXPOSE`) and compose (`ports:`) should list only ports the service actually uses.

**Risk.** Spare ports widen the attack surface.

**Audit.**
```bash
docker ps --quiet | xargs docker inspect --format '{{ .Id }}: Ports={{ .NetworkSettings.Ports }}'
```

**Remediation.** Trim `EXPOSE`. Never use `docker run -P` / `--publish-all`. Prefer `docker run -p 127.0.0.1:8080:8080` (bind to loopback when fronted by a reverse proxy).

---

### 5.28 — Ensure Docker commands always use the latest version of the image

**Description.** Don't rely on locally cached images when upstream has changed.

**Risk.** Running old images means running known CVEs.

**Audit.** Compare local tag vs registry. `docker pull` should fetch a new digest when one exists.

**Remediation.** Pin images by **digest** (`image@sha256:…`) — `latest` is still vulnerable to cache poisoning. Apply to base images, package sources, and deployed image references. Automate digest bumps via Renovate / Dependabot.

---

## Auditor notes

- A `FAIL` needs evidence (file:line or a command's output). Without evidence, mark `MANUAL`.
- For upstream images the project doesn't build (e.g., `postgres:16`), controls 4.1 / 4.3 / 4.6 can be `MANUAL` if upstream already complies — document the rationale in the report.
- Controls 4.4 and 5.28 are the only ones that require looking at **CI** rather than just the Dockerfile. If there's no visible pipeline → `MANUAL`.
- Other CIS controls outside this Level-1 subset (host configuration, daemon configuration, swarm-specific items) are out of scope here. Surface them as "informational" in the report if relevant.
