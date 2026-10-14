#!/usr/bin/env bash
# One-time: build LibreDWG's `dwg2dxf` so the console can import .dwg floor plans directly.
#   cd /opt/site-comms && ./tools/install-dwg-support.sh
# LibreDWG is GPL-3; it is built as a separate program and run via subprocess (never linked).
# Takes a few minutes. Installs to server/bin/dwg2dxf, which the importer finds automatically.
set -euo pipefail
VER="0.13.3"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="$APP_DIR/server/bin"
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

if [ -x "$BIN_DIR/dwg2dxf" ] && [ "${1:-}" != "--force" ]; then
  echo "dwg2dxf already installed at $BIN_DIR/dwg2dxf (use --force to rebuild)"; exit 0
fi

if ! command -v gcc >/dev/null || ! command -v make >/dev/null; then
  $SUDO apt-get update -q && $SUDO apt-get install -y -q build-essential
fi
command -v curl >/dev/null || $SUDO apt-get install -y -q curl
command -v xz   >/dev/null || $SUDO apt-get install -y -q xz-utils

# small servers can run out of memory with parallel compiles
MEM_GB=$(awk '/MemTotal/{print int($2/1048576)}' /proc/meminfo)
JOBS=1; [ "$MEM_GB" -ge 2 ] && JOBS="$(nproc)"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
echo "Downloading LibreDWG $VER ..."
curl -fsSL -o "$TMP/libredwg.tar.xz" "https://github.com/LibreDWG/libredwg/releases/download/$VER/libredwg-$VER.tar.xz"
mkdir "$TMP/src" && tar -xf "$TMP/libredwg.tar.xz" -C "$TMP/src" --strip-components=1
cd "$TMP/src"
echo "Configuring ..."
./configure --disable-bindings --disable-python --disable-shared --disable-werror -q >/dev/null
echo "Building with $JOBS job(s) (a few minutes) ..."
make -C src -j"$JOBS" -s
make -C programs dwg2dxf -j"$JOBS" -s

$SUDO mkdir -p "$BIN_DIR"
$SUDO install -m 755 -s programs/dwg2dxf "$BIN_DIR/dwg2dxf"
echo "Installed: $("$BIN_DIR/dwg2dxf" --version 2>&1 | head -1)"
echo "Restart not required - the next .dwg upload will use it."
