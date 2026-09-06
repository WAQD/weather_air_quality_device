#!/bin/bash
# Prepare the local, rootless QEMU Raspberry Pi OS test environment.
#
# This script does not use sudo, mount disk images, or modify the downloaded
# base image. It creates a disposable SSH key and a prepared image under the
# cache directory, then writes a Fish/Bash environment file for pytest.
#
# Usage:
#   ./script/os_test/setup_qemu.sh
#   source ~/.cache/waqd-os-test/qemu-env.fish
#   ./script/os_test/dev_os_test.sh rpios

set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
CACHE_DIR="${WAQD_RPIOS_CACHE_DIR:-$HOME/.cache/waqd-os-test}"
BASE_IMAGE="${WAQD_RPIOS_IMAGE:-}"
FORCE=0
CHECK_ONLY=0

usage() {
    cat >&2 <<'EOF'
Usage: setup_qemu.sh [options]

Options:
  --image PATH        official Raspberry Pi OS image; fetches one if omitted
  --cache-dir PATH    artifact directory (default: ~/.cache/waqd-os-test)
  --force             recreate the prepared image and SSH key
  --check             only check host prerequisites; do not create anything
  -h, --help          show this help

The kernel and boot files are extracted from the official image and QEMU uses
the Raspberry Pi 3B machine model. No external kernel is required.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --image) BASE_IMAGE="${2:?--image needs a path}"; shift 2 ;;
        --cache-dir) CACHE_DIR="${2:?--cache-dir needs a path}"; shift 2 ;;
        --force) FORCE=1; shift ;;
        --check) CHECK_ONLY=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

CACHE_DIR=$(realpath -m "$CACHE_DIR")
mkdir -p "$CACHE_DIR"

missing=()
for tool in ssh-keygen qemu-img qemu-system-aarch64 guestfish virt-customize; do
  command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
command -v virt-customize >/dev/null 2>&1 || missing+=("virt-customize")
if [ "${#missing[@]}" -gt 0 ]; then
  echo "ERROR: missing required host tools: ${missing[*]}" >&2
  echo "Install QEMU and guestfs tools. On Arch/CachyOS:" >&2
  echo "  sudo pacman -S --needed qemu-system-aarch64 guestfs-tools openssh" >&2
  echo "Then rerun this setup script." >&2
  exit 2
fi

if [ "$CHECK_ONLY" = 1 ]; then
  echo "QEMU setup prerequisites are installed."
  exit 0
fi

KEY="$CACHE_DIR/qemu-test-key"
PREPARED="$CACHE_DIR/raspios-qemu-prepared.img"
KERNEL="$CACHE_DIR/kernel8.img"
ENV_FILE="$CACHE_DIR/qemu-env.fish"
ENV_BASH="$CACHE_DIR/qemu-env.sh"

if [ "$FORCE" = 1 ] || [ ! -f "$KEY" ] || [ ! -f "$KEY.pub" ]; then
    rm -f "$KEY" "$KEY.pub"
    ssh-keygen -q -t ed25519 -N '' -f "$KEY" -C waqd-qemu-test
    chmod 600 "$KEY"
fi

if [ -z "$BASE_IMAGE" ]; then
    FETCH="$ROOT/script/os_test/fetch_rpios_image.sh"
    BASE_IMAGE=$("$FETCH" "$CACHE_DIR")
fi
BASE_IMAGE=$(realpath "$BASE_IMAGE")
[ -f "$BASE_IMAGE" ] || { echo "ERROR: base image not found: $BASE_IMAGE" >&2; exit 2; }

if [ "$FORCE" = 1 ] || [ ! -f "$PREPARED" ]; then
    rm -f "$PREPARED"
    "$ROOT/script/os_test/prepare_qemu_guest.sh" "$BASE_IMAGE" "$KEY.pub" "$PREPARED"
fi

if [ "$FORCE" = 1 ] || [ ! -f "$KERNEL" ]; then
    # The official image has a separate FAT boot partition, so `-i` alone
    # mounts only the root ext4 partition and cannot see /boot/kernel8.img.
    guestfish --ro -a "$BASE_IMAGE" <<EOF
run
mount /dev/sda2 /
mount /dev/sda1 /boot
download /boot/kernel8.img $KERNEL
EOF
fi
[ -s "$KERNEL" ] || { echo "ERROR: official image does not contain boot/kernel8.img" >&2; exit 2; }

cat > "$ENV_FILE" <<EOF
set -gx WAQD_QEMU_KERNEL '$KERNEL'
set -gx WAQD_QEMU_SSH_KEY '$KEY'
set -gx WAQD_RPIOS_IMAGE '$PREPARED'
set -gx WAQD_OS_TEST 1
EOF
cat > "$ENV_BASH" <<EOF
export WAQD_QEMU_KERNEL=$(printf '%q' "$KERNEL")
export WAQD_QEMU_SSH_KEY=$(printf '%q' "$KEY")
export WAQD_RPIOS_IMAGE=$(printf '%q' "$PREPARED")
export WAQD_OS_TEST=1
EOF
chmod 600 "$ENV_FILE" "$ENV_BASH"

cat <<EOF
QEMU test environment is ready.

Fish:
  source '$ENV_FILE'
  ./script/os_test/dev_os_test.sh rpios

Bash:
  source '$ENV_BASH'
  ./script/os_test/dev_os_test.sh rpios

Artifacts:
  base image: $BASE_IMAGE
  prepared image: $PREPARED
  private key: $KEY
  environment: $ENV_FILE
EOF
