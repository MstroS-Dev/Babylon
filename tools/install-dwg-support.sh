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

# One source file (decode.c) needs ~1.3 GB of RAM to compile, which small servers don't have;
# the compiler then gets "Killed". So: make sure RAM + swap >= 3 GB (adding a TEMPORARY swap file
# that is removed again afterwards), compile with lighter flags, and use one job on small machines.
MEM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
SWAP_MB=$(awk '/SwapTotal/{print int($2/1024)}' /proc/meminfo)
NEED_MB="${DWG_BUILD_NEED_MB:-3072}"   # override only for testing
SWAPFILE=""
TMP="$(mktemp -d)"
cleanup() {
  if [ -n "$SWAPFILE" ]; then $SUDO swapoff "$SWAPFILE" 2>/dev/null || true; $SUDO rm -f "$SWAPFILE"; fi
  rm -rf "$TMP"
}
trap cleanup EXIT

if [ $((MEM_MB + SWAP_MB)) -lt $NEED_MB ]; then
  ADD_MB=$((NEED_MB - MEM_MB - SWAP_MB)); [ "$ADD_MB" -lt 1024 ] && ADD_MB=1024
  FREE_MB=$(df -Pm /var/tmp | awk 'NR==2{print $4}')
  if [ "$FREE_MB" -lt $((ADD_MB + 700)) ]; then
    echo "Not enough free disk space (${FREE_MB} MB free; need about $((ADD_MB + 700)) MB). Free some space and re-run."; exit 1
  fi
  echo "Server has ${MEM_MB} MB RAM: adding ${ADD_MB} MB of temporary swap for the build ..."
  SWAPFILE=/var/tmp/dwg-build.swap
  $SUDO rm -f "$SWAPFILE"
  $SUDO dd if=/dev/zero of="$SWAPFILE" bs=1M count="$ADD_MB" status=none
  $SUDO chmod 600 "$SWAPFILE"
  $SUDO mkswap "$SWAPFILE" >/dev/null
  $SUDO swapon "$SWAPFILE"
fi

JOBS=1; [ "$MEM_MB" -ge 4096 ] && JOBS="$(nproc)"

echo "Downloading LibreDWG $VER ..."
curl -fsSL -o "$TMP/libredwg.tar.xz" "https://github.com/LibreDWG/libredwg/releases/download/$VER/libredwg-$VER.tar.xz"
mkdir "$TMP/src" && tar -xf "$TMP/libredwg.tar.xz" -C "$TMP/src" --strip-components=1
cd "$TMP/src"
echo "Configuring ..."
CFLAGS="-O1 -g0" ./configure --disable-bindings --disable-python --disable-shared --disable-werror -q >/dev/null 2>&1
echo "Building with $JOBS job(s). On a small server this can take 15-30 minutes - it is working, just slow ..."
make -C src -j"$JOBS" -s
make -C programs dwg2dxf -j"$JOBS" -s

$SUDO mkdir -p "$BIN_DIR"
$SUDO install -m 755 -s programs/dwg2dxf "$BIN_DIR/dwg2dxf"
echo "Installed: $("$BIN_DIR/dwg2dxf" --version 2>&1 | head -1)"
echo "Restart not required - the next .dwg upload will use it."
