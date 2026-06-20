---
name: docker-hardening
description: >
  Comprehensive, stack-agnostic Docker security skill. Combines the CIS Docker Benchmark
  (Level 1) audit with a 7-layer defense-in-depth model — image, build, runtime, network,
  host, orchestration, monitoring. Use when the user asks to "harden Docker", "hardenize
  containers", "audit Dockerfile security", "review compose security", "container security
  review", "fix CIS Docker findings", "non-root container", "drop capabilities",
  "scan images" (Docker Scout / Trivy / Grype / Snyk), "remove secrets from Dockerfile",
  "SBOM / supply chain / image signing / cosign / content trust", "BuildKit secrets / frontend
  pinning", "seccomp / AppArmor / SELinux profile", "user namespaces / rootless docker",
  "Falco / runtime monitoring", "CIS Docker Benchmark", "docker-bench-security". Works for any
  language or framework. Discovers all Dockerfiles + compose files, runs the audit, writes a
  remediation report, and (with user consent) applies fixes.
---

# Docker Hardening

Audit and harden Docker artifacts against a layered security model. Backbone: the 12 **CIS Docker Benchmark — Level 1** controls. Extended with: minimal/distroless images, supply-chain integrity (SBOM + signing + BuildKit frontend pinning), runtime profiles (capabilities, seccomp, AppArmor/SELinux, user namespaces, rootless Docker), network segmentation, secrets management, and runtime monitoring.

The skill is **prescriptive** (fixed audit shape) and **stack-agnostic** (works for Node, Python, Go, Java, .NET, Ruby, PHP, Rust, etc. — choose the matching snippet from `references/`).

---

## 1. When to activate

Trigger if the user wants any of these:

| Intent | Examples |
|---|---|
| Audit | "harden / hardenize Docker", "audit Dockerfile security", "review my compose for security", "CIS Docker compliance", "docker-bench" |
| Build hardening | "non-root container", "remove secrets from Dockerfile", "BuildKit secrets", "pin base image digest" |
| Runtime hardening | "drop capabilities", "read-only filesystem", "no-new-privileges", "seccomp / AppArmor / SELinux", "user namespaces", "rootless docker" |
| Supply chain | "scan image" (Scout / Trivy / Grype / Snyk), "SBOM", "sign image" (cosign / DCT), "verify provenance", "pin BuildKit frontend" |
| Network / secrets | "network segmentation", "internal network", "expose only the port", "docker secrets / swarm secrets", "vault for container secrets" |
| Monitoring | "Falco", "runtime detection", "docker events", "container audit logging" |

Skip if the user only wants Dockerfile *style* refactoring with no security angle — point them to general Docker docs instead.

---

## 2. Working principles

- **Stack agnostic.** Detect language by reading `FROM` + lockfiles. Adapt snippets from `references/remediations.md`.
- **Evidence-based.** Every PASS/FAIL must cite `file:line` or a command's output. Without evidence → `MANUAL`.
- **Minimum-diff fixes.** Smallest change that closes each FAIL. Never bundle unrelated refactors.
- **Consent before mutating.** Always show the diff before applying.
- **Defense in depth.** Don't treat a single control as "the fix" — every layer of [Section 4](#4-defense-in-depth-7-layers) reduces blast radius if another fails.

---

## 3. Audit workflow

### Phase 0 — Scope & discovery

1. Confirm scope in one short message: *"Auditing all Dockerfiles + compose files in this repo against the 12 CIS Level-1 controls + the 7-layer defense-in-depth checklist. OK?"* Accept narrower scope (single image / service) if offered.
2. Discover artifacts:
   ```bash
   find . -maxdepth 5 -type f \( \
        -iname "Dockerfile*" \
     -o -iname "Containerfile*" \
     -o -iname "docker-compose*.yml" \
     -o -iname "docker-compose*.yaml" \
     -o -iname "compose*.yml" \
     -o -iname "compose*.yaml" \
     -o -iname ".dockerignore" \
   \) \
     | grep -Ev '/(node_modules|\.next|\.venv|venv|dist|build|target|vendor|\.git)/'
   ```
3. If `docker` is available **and** the user wants a runtime audit, list running containers + images:
   ```bash
   docker ps --quiet
   docker images
   ```
4. Read each Dockerfile / compose file before scoring — no scoring from memory.
5. Detect language/package manager from `FROM` and copied lockfiles → use it to pick remediation variants.

### Phase 1 — Score the audit

Score each artifact against the audit matrix below. Use this rubric:

| Result | Meaning |
|---|---|
| `PASS` | Control is satisfied. Cite file:line. |
| `FAIL` | Control is violated. Cite the offending line. |
| `N/A` | Control doesn't apply (one-line reason). |
| `MANUAL` | Needs human verification (e.g., base-image trust, CI scan presence, registry policy). |

#### A — CIS Level-1 controls (mandatory, 12 items)

| # | CIS § | Control | Quick check |
|---|---|---|---|
| A1 | 4.1 | Non-root user | `USER <name-or-uid>` before final `CMD`/`ENTRYPOINT`. |
| A2 | 4.3 | Minimal packages | Minimal base (alpine / slim / distroless / scratch); only required packages installed. |
| A3 | 4.6 | HEALTHCHECK present | Dockerfile `HEALTHCHECK …` **or** compose `healthcheck:`. |
| A4 | 4.7 | Update+install in one layer | `update && install` chained with `&&`; packages pinned; no orphan update. |
| A5 | 4.9 | COPY over ADD | No `ADD` (except local tar extraction with justifying comment). |
| A6 | 4.11 | Verified packages | Signed repos / checksums / lockfile integrity. |
| A7 | 5.28 | Pinned image versions | `FROM image:tag@sha256:…` digest (preferred). Never `:latest`. |
| A8 | 5.7 | No sshd in container | No `openssh-server` installed, no `sshd` running. |
| A9 | 5.9 | Only necessary ports | `EXPOSE` and compose `ports:` minimal; never `-P` / `--publish-all`. |
| A10 | 4.2 | Trusted base image | Official / Verified / mirror / distroless / Wolfi (Chainguard). MANUAL unless mirror enforced. |
| A11 | 4.4 | Scanned + rebuilt | CI runs `docker scout cves` / `trivy image` / `grype` with `--exit-code 1`. MANUAL — check CI. |
| A12 | 4.10 | No secrets in Dockerfile | No `ENV`/`ARG` with credentials; secrets via BuildKit `--mount=type=secret` or runtime env. |

Full text + auditor commands: [`references/cis-controls.md`](references/cis-controls.md).

#### B — Compose runtime hardening (when compose files exist)

| # | Control |
|---|---|
| B1 | `read_only: true` + explicit `tmpfs:` for writable paths |
| B2 | `cap_drop: ["ALL"]`, `cap_add` only what's needed (commonly `NET_BIND_SERVICE`) |
| B3 | `security_opt: ["no-new-privileges:true"]` on every service |
| B4 | `user: "1001:1001"` non-root UID:GID matching the Dockerfile `USER` |
| B5 | Bind mounts use `:ro` unless writes required |
| B6 | Resource limits: `deploy.resources.limits` (cpu + memory) or `mem_limit` / `cpus` / `pids_limit` |
| B7 | No `privileged: true` (outside dedicated DinD runner) |
| B8 | Internal networks (`internal: true`) for service-to-service; only edge services map ports |
| B9 | `secrets:` block (not `environment:`) for sensitive values |
| B10 | Bounded `logging.options.max-size/max-file` |
| B11 | `restart:` policy set (`unless-stopped` / `on-failure`) — prevents silent crashes |
| B12 | `init: true` (PID 1 reaper) for proper signal handling |

Snippets: [`references/remediations.md`](references/remediations.md).

#### C — Supply chain (build + registry)

| # | Control |
|---|---|
| C1 | BuildKit frontend pinned: `# syntax=docker/dockerfile:1` (or with `@sha256:`); never untrusted frontends |
| C2 | SBOM generated: `docker buildx build --sbom=true …` or `syft <image>` in CI |
| C3 | Provenance attestation: `--provenance=true` (SLSA Level 2+) |
| C4 | Image signed: `cosign sign` (preferred) or Docker Content Trust |
| C5 | Registry pulls verified: `cosign verify` in deploy step / admission controller |
| C6 | Base images from low-CVE source (Wolfi / Chainguard / distroless) when feasible |
| C7 | Renovate/Dependabot auto-bumping digests via PR |
| C8 | `.dockerignore` excludes `.env`, `*.pem`, `.git`, `node_modules`, secrets directories |

Snippets: [`references/advanced-hardening.md`](references/advanced-hardening.md) §A — Supply chain.

#### D — Daemon / host (only score if user grants host access)

| # | Control |
|---|---|
| D1 | Docker daemon running on the latest stable release |
| D2 | `/etc/docker/daemon.json`: `"icc": false`, `"userns-remap": "default"`, `"no-new-privileges": true`, `"live-restore": true` |
| D3 | Audit rules for `/var/lib/docker`, `/etc/docker`, `dockerd` binary (auditd) |
| D4 | Rootless Docker considered for multi-tenant or untrusted workloads |
| D5 | SELinux / AppArmor enabled at host level; default Docker profile loaded |
| D6 | `docker-bench-security` clean run (or documented exceptions) |

Snippets: [`references/advanced-hardening.md`](references/advanced-hardening.md) §D — Host & daemon configuration.

#### E — Runtime profiles (advanced)

| # | Control |
|---|---|
| E1 | Seccomp profile applied (default or tighter custom) |
| E2 | AppArmor profile applied (Linux) or SELinux labels (`:Z`/`:z` on volumes) |
| E3 | User namespaces enabled (`userns-remap`) or rootless mode |
| E4 | `--pid=host` / `--network=host` / `--ipc=host` not used |
| E5 | Docker socket (`/var/run/docker.sock`) not mounted into containers |
| E6 | `--device` exposures minimal and justified |

#### F — Monitoring & detection

| # | Control |
|---|---|
| F1 | Centralized log driver (`syslog`, `journald`, `fluentd`, `awslogs`, etc.) — not just json-file |
| F2 | Container start/stop/exec events shipped to SIEM (`docker events` → collector) |
| F3 | Runtime threat detection: Falco (or equivalent) deployed |
| F4 | Image vulnerability scans fire alerts on new CVEs in deployed images |

### Phase 2 — Report

Write the report to a sensible repo path:

- `docs/security/docker-hardening-report.md` if `docs/` exists
- `security/docker-hardening-report.md` if `security/` exists
- `docker-hardening-report.md` at repo root otherwise

Create parent folders as needed. **Never inline the full report in chat** — chat gets only the summary table + the report path.

Report structure:

```markdown
# Docker Hardening Audit — <YYYY-MM-DD>

## Scope
- Repo: <path>
- Artifacts: <list>
- Tooling assumed available: <docker version output, or "not run">

## Summary
| File | A (CIS) | B (Compose) | C (Supply) | D (Daemon) | E (Profiles) | F (Monitor) |
|------|---------|-------------|------------|------------|--------------|-------------|
| backend/Dockerfile        | 8 PASS / 3 FAIL / 1 N/A / 0 MAN | — | 3/5 | — | — | — |
| backend/docker-compose.yml | — | 7/12 | — | — | — | — |
| ...                       | ... | ... | ... | ... | ... | ... |

## Findings by file

### backend/Dockerfile
- [FAIL] **A1 / CIS 4.1 — Non-root user**: no `USER` directive.
  - Evidence: `backend/Dockerfile` has no `USER` (lines 1–22).
  - Fix: see "Remediations" §CIS 4.1.
- [PASS] **A5 / CIS 4.9 — COPY over ADD**: only COPY used.
- ...

### backend/docker-compose.prod.yml
- [FAIL] **B1 — read_only**: backend service is read/write.
- [FAIL] **B3 — no-new-privileges**: missing on all services.
- ...

## Remediations
For each FAIL — concrete paste-ready diff/snippet adapted to the project's stack.

## Manual review checklist
- A10/A11: confirm base image source and CI scan presence.
- D1–D6: host audit out of scope unless host access granted.

## Recommendations (not failures)
- Consider Wolfi/Chainguard for base images (zero-CVE goal).
- Consider rootless Docker for the runtime.
```

### Phase 3 — Apply fixes (only with explicit consent)

After delivering the report, ask: *"Want me to apply the FAIL remediations? I'll show each diff first."* For each remediation:

1. Show the exact diff.
2. Apply via Edit/Write.
3. Mentally re-score the affected control to confirm PASS.

Never auto-apply. Never bundle unrelated refactors. Don't switch base-image families (e.g., debian → alpine → distroless) as part of a fix unless the user explicitly asked — surface that as a recommendation.

---

## 4. Defense in depth — 7 layers

This is the mental model. Every audit category in Phase 1 belongs to one of these layers. When recommending fixes, name the layer so the user sees what's being reinforced.

| Layer | What it protects against | Audit categories |
|---|---|---|
| **1. Image** | Vulnerable / malicious base, oversized attack surface | A2, A3, A6, A7, A10, A11, C6 |
| **2. Build** | Secret leakage, supply-chain tampering, cache poisoning | A4, A5, A12, C1–C5, C7, C8 |
| **3. Runtime** | Container breakout, privilege escalation | A1, A8, B1–B7, B11, B12, E1–E6 |
| **4. Network** | Lateral movement, exposed services | A9, B5, B8 |
| **5. Host** | Daemon compromise, host privilege abuse | D1–D6 |
| **6. Orchestration** | RBAC misuse, weak secrets handling | B9, C5 |
| **7. Monitoring** | Late detection of breach / abuse | A3 (HEALTHCHECK), A11, B10, F1–F4 |

### Least privilege checklist

Apply at every layer:
- Non-root user
- Dropped capabilities (`cap_drop: ALL` + selective `cap_add`)
- Read-only root filesystem
- Minimal network exposure (localhost binds, internal networks)
- Restricted syscalls (seccomp profile)
- Bounded resources (cpu/memory/pids)
- No host namespaces, no host devices, no docker socket
- Time-bound, scoped credentials (no long-lived tokens)

---

## 5. Anti-patterns the audit must flag

- `FROM <anything>:latest` — pin the tag, ideally the digest. **FAIL**.
- `ENV API_KEY=…` / `ARG GITHUB_TOKEN=…` / `COPY .env …` / `COPY id_rsa …` — secrets in layers. **FAIL**.
- `RUN apt-get update` on its own line. **FAIL**.
- `ADD http://…` — remote fetch without checksum. **FAIL**.
- `USER root` after the last functional step. **FAIL**.
- `privileged: true` in compose (outside docker-in-docker runners). **FAIL**.
- `-v /var/run/docker.sock:/var/run/docker.sock` inside a non-build container — equivalent to root on host. **FAIL**.
- `--network=host` / `--pid=host` / `--ipc=host` — namespaces broken. **FAIL**.
- `chmod 777` anywhere in the Dockerfile. **FAIL**.
- `docker scan` (deprecated) in CI — replace with `docker scout` or `trivy`.
- Untrusted BuildKit frontend (`# syntax=` pointing at a non-Docker, non-pinned image). **FAIL**.

---

## 6. Things this skill must NOT do

- Don't apply fixes without showing the diff first.
- Don't "wholesale rewrite" a Dockerfile — minimum diff per FAIL.
- Don't declare PASS without file:line evidence.
- Don't invent CIS section numbers — stick to the 12 listed in Section 3A.
- Don't run deprecated tooling (`docker scan`, `notary`).
- Don't change the user's base-image family without consent — recommend, don't impose.
- Don't write Spanish/English mixed prose in the report — match the user's language.
- Don't audit host (D) without confirmed host access.

---

## 7. References

| File | What's in it |
|---|---|
| [`references/cis-controls.md`](references/cis-controls.md) | Full text of the 12 CIS Level-1 controls — description, risk, auditor procedure, remediation |
| [`references/remediations.md`](references/remediations.md) | Paste-ready Dockerfile + compose snippets for every control, with variants per package manager (apt / apk / dnf) and per language (Node / Python / Go / Java / .NET / Ruby / PHP / Rust) |
| [`references/advanced-hardening.md`](references/advanced-hardening.md) | Supply chain (SBOM, signing, BuildKit frontend), runtime profiles (seccomp, AppArmor, SELinux), user namespaces, rootless Docker, host daemon config, monitoring (Falco, docker events, audit) |
| [`references/checklist.md`](references/checklist.md) | Flat pre-deploy checklist — print-friendly, ~60 items grouped by layer |

External docs:

- CIS Docker Benchmark: https://www.cisecurity.org/benchmark/docker
- docker-bench-security: https://github.com/docker/docker-bench-security
- Docker Engine security: https://docs.docker.com/engine/security/
- Dockerfile best practices: https://docs.docker.com/build/building/best-practices/
- BuildKit secrets: https://docs.docker.com/build/building/secrets/
- Docker Scout: https://docs.docker.com/scout/
- Trivy: https://aquasecurity.github.io/trivy/
- Grype: https://github.com/anchore/grype
- Syft (SBOM): https://github.com/anchore/syft
- Cosign (signing): https://docs.sigstore.dev/cosign/overview/
- Falco (runtime detection): https://falco.org/
- Wolfi (low-CVE base): https://wolfi.dev/
- Chainguard Images: https://images.chainguard.dev/
- Rootless Docker: https://docs.docker.com/engine/security/rootless/
