# Docker hardening — flat pre-deploy checklist

~60 items, grouped by defense-in-depth layer. Use to print or paste into a PR description. Each item is a yes/no question. Map to the audit categories in `SKILL.md` §3.

---

## Layer 1 — Image

- [ ] **I1.** Base image is a Docker Official Image, Verified Publisher, internal mirror, distroless, or Wolfi/Chainguard. *(A10, C6)*
- [ ] **I2.** Base image pinned by digest: `FROM image:tag@sha256:…`. *(A7, C7)*
- [ ] **I3.** Final stage uses a minimal base (slim / alpine / distroless / scratch). *(A2, G)*
- [ ] **I4.** Only required packages installed (`--no-install-recommends`, `--no-cache`). *(A2)*
- [ ] **I5.** Image rebuilt at least weekly to pull in upstream patches. *(A11)*
- [ ] **I6.** No `openssh-server`, no `sshd`, no editor/debugger in production image. *(A8)*

## Layer 2 — Build

- [ ] **B1.** `# syntax=docker/dockerfile:1` (or pinned by digest). No untrusted frontends. *(C1)*
- [ ] **B2.** Multi-stage build — final stage carries no build tools or compilers.
- [ ] **B3.** `COPY` everywhere; `ADD` only with checksum/justification. *(A5)*
- [ ] **B4.** Package install steps chained with update (`RUN … update && … install …`), versions pinned. *(A4)*
- [ ] **B5.** No `ENV`/`ARG` containing secrets, tokens, or private keys. *(A12)*
- [ ] **B6.** No `COPY .npmrc / .netrc / id_rsa / .env / secrets/` into the image. *(A12)*
- [ ] **B7.** Build-time secrets via `RUN --mount=type=secret …` (BuildKit). *(A12)*
- [ ] **B8.** Lockfile-driven installs (`npm ci`, `pip --require-hashes`, `bundle install --deployment`, etc.). *(A6)*
- [ ] **B9.** External binaries verified with `sha256sum --check` or `gpg --verify`. *(A6)*
- [ ] **B10.** SBOM generated (`docker buildx --sbom=true` or `syft`) and stored as an artifact. *(C2)*
- [ ] **B11.** Provenance attestation `--provenance=true` (SLSA Level 2+). *(C3)*
- [ ] **B12.** Image signed (cosign keyless / KMS) on push. *(C4)*
- [ ] **B13.** Image scanned in CI with `--exit-code 1` on HIGH/CRITICAL (Scout / Trivy / Grype). *(A11)*
- [ ] **B14.** `.dockerignore` excludes secrets, VCS, IDE, build artifacts. *(C8)*

## Layer 3 — Runtime (image-level + compose-level)

- [ ] **R1.** `USER` directive set to a non-root UID:GID in the Dockerfile. *(A1)*
- [ ] **R2.** Compose `user:` matches the Dockerfile `USER`. *(B4)*
- [ ] **R3.** `HEALTHCHECK` defined in Dockerfile or compose. *(A3)*
- [ ] **R4.** `read_only: true` + explicit `tmpfs:` for writable paths. *(B1)*
- [ ] **R5.** `cap_drop: [ALL]`; `cap_add` only what's truly needed. *(B2)*
- [ ] **R6.** `security_opt: ["no-new-privileges:true"]` on every service. *(B3)*
- [ ] **R7.** Seccomp profile applied (`seccomp=default` or stricter custom). *(E1)*
- [ ] **R8.** AppArmor (Linux) or SELinux labels enforced. *(E2)*
- [ ] **R9.** Resource limits: `cpus`, `memory`, `pids_limit`. *(B6)*
- [ ] **R10.** `restart:` policy set (`unless-stopped` / `on-failure`). *(B11)*
- [ ] **R11.** `init: true` (PID 1 reaper) — signals propagate, zombies reaped. *(B12)*
- [ ] **R12.** Bind mounts use `:ro` unless writes are required. *(B5)*
- [ ] **R13.** No `privileged: true` (outside dedicated DinD runner). *(B7)*
- [ ] **R14.** No host namespaces: no `--network=host`, `--pid=host`, `--ipc=host`, `--uts=host`. *(E4)*
- [ ] **R15.** Docker socket NOT mounted into the container (`/var/run/docker.sock`). *(E5)*
- [ ] **R16.** `--device` exposures minimal and justified. *(E6)*

## Layer 4 — Network

- [ ] **N1.** Only required ports in `EXPOSE` / `ports:`; never `-P` / `--publish-all`. *(A9)*
- [ ] **N2.** Published ports bound to `127.0.0.1` when fronted by a reverse proxy.
- [ ] **N3.** User-defined networks; internal services on `internal: true`. *(B8, E1)*
- [ ] **N4.** Default bridge `icc: false` at the daemon level. *(D2, E2)*
- [ ] **N5.** Egress controlled (per-network iptables, sidecar proxy, or service mesh). *(E5)*

## Layer 5 — Host & daemon

- [ ] **H1.** Docker daemon on the latest stable release. *(D1)*
- [ ] **H2.** `/etc/docker/daemon.json` hardened: `icc=false`, `userns-remap`, `no-new-privileges`, `live-restore`, bounded log driver. *(D2)*
- [ ] **H3.** Auditd rules in place for `/etc/docker`, `/var/lib/docker`, dockerd binary. *(D3)*
- [ ] **H4.** User namespaces enabled (`userns-remap=default`) or rootless Docker / Podman. *(D4, E3)*
- [ ] **H5.** Host AppArmor or SELinux enforcing; default Docker profile loaded. *(D5)*
- [ ] **H6.** `docker-bench-security` clean run (or documented exceptions). *(D6)*
- [ ] **H7.** Host kernel current with security patches.

## Layer 6 — Orchestration & secrets

- [ ] **O1.** Secrets via compose `secrets:` block / Swarm secrets / Vault / cloud KMS — not `environment:`. *(B9)*
- [ ] **O2.** Image signatures verified at deploy time (cosign verify / admission controller / Kyverno). *(C5)*
- [ ] **O3.** Renovate / Dependabot configured to bump digests via PR. *(C7)*
- [ ] **O4.** Registry has retention + immutability policies (no `:latest` overwrite for production tags).
- [ ] **O5.** RBAC on the registry: push limited to CI identity; pull limited to deploy identity.
- [ ] **O6.** Build pipeline runs in an ephemeral isolated runner (not shared host).

## Layer 7 — Monitoring & detection

- [ ] **M1.** Centralized log driver (`syslog`/`journald`/`fluentd`/`awslogs`/`splunk`) — not just `json-file`. *(F1)*
- [ ] **M2.** Log rotation bounded (`max-size`, `max-file`) when `json-file` is used. *(B10)*
- [ ] **M3.** Container lifecycle events (`docker events`) shipped to SIEM. *(F2)*
- [ ] **M4.** Runtime threat detection: Falco (or equivalent) deployed. *(F3)*
- [ ] **M5.** Nightly vulnerability scans on registry images; alerts on new CVEs in already-deployed images. *(F4)*
- [ ] **M6.** Metrics: container CPU, memory, restart count, healthcheck failures (Prometheus / Datadog).
- [ ] **M7.** Backup/restore tested for stateful volumes.

---

## Severity tagging

Use this when triaging the report:

| Severity | Use when | Examples |
|---|---|---|
| **Critical** | Trivially exploitable, breakouts likely. Block deploy. | `privileged: true`, docker.sock mounted, `--network=host`, secret in `ENV`. |
| **High** | Significant risk; fix before next prod release. | Running as root, no seccomp, no read-only FS, `:latest` tag, `ADD http://` without checksum. |
| **Medium** | Should fix in the next sprint. | No HEALTHCHECK, no resource limits, missing `no-new-privileges`. |
| **Low** | Hygiene; track in backlog. | Suboptimal log driver, missing `init: true`, no SBOM. |
| **Info** | Recommendation, not a finding. | "Consider Wolfi/Chainguard for base image", "consider rootless Docker". |

## Common security mistakes (cheat sheet)

- Hardcoding secrets into the image instead of using runtime env / secrets manager.
- Running as root because "it just works".
- Using `:latest` because pinning is "annoying".
- Mounting the docker socket "because the app needs to spawn containers" — almost always solvable with an API or a sidecar.
- Disabling seccomp/AppArmor "because something didn't work" — usually one syscall fix away.
- Using `privileged: true` as a debugging shortcut and never removing it.
- Treating CI scan results as advisory; not gating the pipeline.
- Pinning a tag but never updating it, leaving CVEs unpatched for months.
- Logging credentials to stdout (later shipped to SIEM in clear).
