#!/usr/bin/env bash
# warm_scanners.sh — cold-start warm-up (spec §7, plan §6).
#
# Run in the SETUP block (0-2h), BEFORE any live scan, as part of VPS provisioning
# (NOT in the path of a scan). Without this, the first `docker run nuclei` tries to
# download 12k+ templates and FAILS by DNS inside the container, so the basic level
# (which is NEVER cut) produces no findings.
#
# What it does:
#   1. docker pull every HEAVY sibling image at its PINNED tag (NEVER :latest).
#   2. nuclei -update-templates ONCE into the persistent `nuclei_templates` volume.
#   3. hexstrike (Kali, several GB) is NOT pre-pulled if time is tight (spec §10).
#
# Idempotent: safe to re-run. `just warm-scanners` wraps it.
set -euo pipefail

# Pinned tags — keep in sync with src/scanning/registry.py (ZAP_IMAGE, HEXSTRIKE_IMAGE).
ZAP_IMAGE="${ZAP_IMAGE:-zaproxy/zap-stable:2.15.0}"
HEXSTRIKE_IMAGE="${HEXSTRIKE_IMAGE:-hexstrike/hexstrike-ai:stable}"
NUCLEI_TEMPLATES_VOLUME="${NUCLEI_TEMPLATES_VOLUME:-backend_nuclei_templates}"
WARM_HEXSTRIKE="${WARM_HEXSTRIKE:-false}"

echo "==> [1/3] Pulling pinned heavy images (never :latest)"
docker pull "${ZAP_IMAGE}"

if [ "${WARM_HEXSTRIKE}" = "true" ]; then
  echo "==> Pulling hexstrike (opt-in; several GB)"
  docker pull "${HEXSTRIKE_IMAGE}"
else
  echo "==> Skipping hexstrike pre-pull (spec §10: cut to zero unless time allows)"
fi

echo "==> [2/3] Ensuring nuclei_templates volume exists"
docker volume create "${NUCLEI_TEMPLATES_VOLUME}" >/dev/null

echo "==> [3/3] Pre-downloading nuclei templates ONCE into the volume"
# Run nuclei from the worker image so we use the SAME pinned nuclei binary. The
# templates land on the persistent volume; every live run then uses -duc to skip
# the (failing) DNS update check.
docker run --rm \
  -v "${NUCLEI_TEMPLATES_VOLUME}:/root/nuclei-templates" \
  --network owliver_egress \
  owliver/worker:local \
  nuclei -update-templates -duc || {
  echo "WARN: nuclei template warm failed; the worker image may not be built yet." >&2
  echo "      Build it first: just build-scanners" >&2
  exit 1
}

echo "==> Warm complete. Heavy images pinned, nuclei templates cached."
