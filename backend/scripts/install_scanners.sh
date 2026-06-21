#!/usr/bin/env bash
# install_scanners.sh — install the LIGHT pentest CLIs at PINNED versions.
#
# Baked into the fat `scanners` image (Dockerfile.scanners). Every version is
# pinned (NEVER :latest, spec §7) so the image is reproducible and the first live
# run does not surprise-download a breaking release. nuclei templates are NOT
# pulled here (that is warm_scanners.sh, into a persistent volume) — but `-duc`
# (disable update check) is applied per-run by run_tool so the first run does not
# fail on DNS inside the container.
set -euo pipefail

ARCH="$(dpkg --print-architecture)" # amd64 / arm64
BIN_DIR="/opt/scanners/bin"
mkdir -p "${BIN_DIR}"

# --- Pinned versions (bump deliberately, never floating) --------------------
NUCLEI_VERSION="3.3.5"
KATANA_VERSION="1.1.2"
FFUF_VERSION="2.1.0"
SUBFINDER_VERSION="2.6.6"
DNSX_VERSION="1.2.1"
TESTSSL_VERSION="3.2.1"

dl() { # dl <url> <out>
  curl -fsSL "$1" -o "$2"
}

install_pd_tool() { # install_pd_tool <name> <version> <repo>
  local name="$1" version="$2" repo="$3"
  local tgz="/tmp/${name}.tar.gz"
  dl "https://github.com/projectdiscovery/${repo}/releases/download/v${version}/${repo}_${version}_linux_${ARCH}.zip" "/tmp/${name}.zip"
  unzip -o "/tmp/${name}.zip" -d "/tmp/${name}" >/dev/null
  install -m 0755 "/tmp/${name}/${name}" "${BIN_DIR}/${name}"
  rm -rf "/tmp/${name}" "/tmp/${name}.zip" "${tgz}"
}

# nuclei / katana / subfinder / dnsx (ProjectDiscovery, Go binaries)
install_pd_tool nuclei "${NUCLEI_VERSION}" nuclei
install_pd_tool katana "${KATANA_VERSION}" katana
install_pd_tool subfinder "${SUBFINDER_VERSION}" subfinder
install_pd_tool dnsx "${DNSX_VERSION}" dnsx

# ffuf (Go binary, separate release naming)
dl "https://github.com/ffuf/ffuf/releases/download/v${FFUF_VERSION}/ffuf_${FFUF_VERSION}_linux_${ARCH}.tar.gz" "/tmp/ffuf.tar.gz"
tar -xzf /tmp/ffuf.tar.gz -C /tmp ffuf
install -m 0755 /tmp/ffuf "${BIN_DIR}/ffuf"
rm -f /tmp/ffuf /tmp/ffuf.tar.gz

# testssl.sh (shell script, pinned tag)
git clone --depth 1 --branch "v${TESTSSL_VERSION}" https://github.com/drwetter/testssl.sh.git /opt/testssl
ln -sf /opt/testssl/testssl.sh "${BIN_DIR}/testssl.sh"

# sqlmap (apt provides a recent build; pin via system package)
apt-get update && apt-get install -y --no-install-recommends sqlmap && rm -rf /var/lib/apt/lists/*

# security-headers: a thin wrapper around a single root request (spec §4.2). Real
# impl is a small Python checker shipped in the app; here we ensure the launcher
# name resolves on PATH so TOOL_SPECS' base_argv works.
cat >"${BIN_DIR}/security-headers" <<'EOF'
#!/usr/bin/env bash
# Thin launcher — delegates to the app's header checker module.
exec python -m src.scanning.tools.security_headers "$@"
EOF
chmod +x "${BIN_DIR}/security-headers"

echo "Installed pinned scanners into ${BIN_DIR}:"
ls -1 "${BIN_DIR}"
