#!/bin/bash
# Boot an ARM64 Raspberry Pi OS disk through QEMU without mounting it on host.
#
# The base image is never modified. QEMU writes only to a disposable qcow2
# overlay in WAQD_QEMU_WORKDIR. The guest must be pre-provisioned with SSH,
# user pi, and the public key matching WAQD_QEMU_SSH_KEY.
#
# Required environment:
#   WAQD_QEMU_WORKDIR       disposable runtime directory
#   WAQD_QEMU_SSH_PORT      host port forwarded to guest port 22
#   WAQD_QEMU_APPEND        kernel command line, including root=/dev/vda2
#   WAQD_QEMU_SSH_KEY       private key used by pytest (guest must be prepared)

set -euo pipefail

IMG="${1:?usage: run_qemu.sh <base-image> <workdir>}"
WORKDIR="${2:?usage: run_qemu.sh <base-image> <workdir>}"
PORT="${WAQD_QEMU_SSH_PORT:?WAQD_QEMU_SSH_PORT is required}"
APPEND="${WAQD_QEMU_APPEND:?WAQD_QEMU_APPEND is required}"
KERNEL="${WAQD_QEMU_KERNEL:-$WORKDIR/kernel8.img}"

for tool in qemu-system-aarch64 qemu-img; do
    command -v "$tool" >/dev/null || { echo "ERROR: $tool is required" >&2; exit 2; }
done
[ -f "$IMG" ] || { echo "ERROR: image not found: $IMG" >&2; exit 2; }
[ -f "$KERNEL" ] || { echo "ERROR: kernel not found: $KERNEL" >&2; exit 2; }
mkdir -p "$WORKDIR"
if [ -z "${WAQD_QEMU_SSH_KEY:-}" ]; then
    echo "ERROR: WAQD_QEMU_SSH_KEY is required; prepare the guest image first" >&2
    exit 2
fi
OVERLAY="$WORKDIR/root.qcow2"
qemu-img create -q -f qcow2 -F raw -b "$IMG" "$OVERLAY"

cleanup() {
    status=$?
    rm -f "$OVERLAY"
    exit "$status"
}
trap cleanup EXIT INT TERM

QEMU=(
    qemu-system-aarch64
    -machine raspi3b
    -cpu cortex-a53
    -smp "${WAQD_QEMU_SMP:-4}"
    -m "${WAQD_QEMU_MEMORY:-2048}"
    -nographic
    -serial "file:$WORKDIR/serial.log"
    -monitor none
    -drive "if=none,id=disk,format=qcow2,file=$OVERLAY"
    -device sd-card,drive=disk
    -nic "user,model=virtio,hostfwd=tcp:127.0.0.1:$PORT-:22"
    -kernel "$KERNEL"
    -append "$APPEND"
)
exec "${QEMU[@]}"
