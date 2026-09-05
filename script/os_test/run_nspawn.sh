#!/bin/bash
# Boot the OFFICIAL Raspberry Pi OS image with systemd-nspawn.
#
# Why nspawn instead of docker:
#   * The real image is a partitioned disk image, not a tarball. `losetup
#     --partscan` + mount gives us the actual rootfs - no `docker import` of a
#     guestfish dump, no unofficial base image.
#   * `systemd-nspawn --boot` runs a genuine PID 1 inside the machine, so a
#     `reboot` issued by the installer restarts the container's init instead of
#     the host. This is the only tier that exercises the reboot for real.
#
# Usage (needs root):
#   sudo ./script/os_test/run_nspawn.sh <image.img> [machine-name]
#
# Env:
#   WAQD_REPO       - repo root to bind-mount at /waqd
#   WAQD_NSPAWN_MNT - reuse a prepared rootfs mount instead of mounting image
#   WAQD_REFRESH=1  - discard/recreate the prepared mount

set -euo pipefail

IMG="${1:?usage: run_nspawn.sh <image.img> [machine-name]}"
MACHINE="${2:-waqd-os-test}"
REPO="${WAQD_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
MNT="${WAQD_NSPAWN_MNT:-}"
LOOP=""

cleanup() {
    local status=$?
    if [ -n "$MNT" ] && [ "${WAQD_KEEP_MOUNT:-0}" != "1" ]; then
        umount -R -l "$MNT" 2>/dev/null || true
        rmdir "$MNT" 2>/dev/null || true
    fi
    if [ -n "$LOOP" ] && [ "${WAQD_KEEP_MOUNT:-0}" != "1" ]; then
        losetup --detach "$LOOP" 2>/dev/null || true
    fi
    exit "$status"
}
trap cleanup EXIT INT TERM

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: needs root for losetup/mount/systemd-nspawn" >&2
    exit 1
fi

for tool in losetup mount systemd-nspawn; do
    command -v "$tool" >/dev/null || { echo "ERROR: $tool not found" >&2; exit 1; }
done

if [ -n "$MNT" ] && [ "${WAQD_REFRESH:-0}" != "1" ] && [ -d "$MNT/etc" ]; then
    echo "Reusing prepared rootfs at $MNT"
    LOOP=""
else
    # --- attach the image and find its rootfs partition ---------------------
    LOOP=$(losetup --partscan --find --show "$IMG")
    echo "Attached $IMG at $LOOP"
    partprobe "$LOOP" 2>/dev/null || true
    sleep 1

# The rootfs is the larger of the two partitions (boot is ~512M FAT).
ROOT_PART=""
for part in "${LOOP}"p*; do
    [ -b "$part" ] || continue
    if [ -z "$ROOT_PART" ]; then
        ROOT_PART="$part"
    else
        CUR=$(blockdev --getsize64 "$part")
        BEST=$(blockdev --getsize64 "$ROOT_PART")
        [ "$CUR" -gt "$BEST" ] && ROOT_PART="$part"
    fi
done
    [ -n "$ROOT_PART" ] || { echo "ERROR: no partitions found on $LOOP" >&2; exit 1; }
    echo "Rootfs partition: $ROOT_PART"

    MNT="${MNT:-$(mktemp -d /tmp/waqd-nspawn.XXXXXX)}"
    mkdir -p "$MNT"
    mount "$ROOT_PART" "$MNT"
    echo "Mounted rootfs at $MNT"
fi

# --- first-boot preparation -------------------------------------------------
# Enable passwordless sudo and make sure the `pi` user exists, matching the
# real device. Raspberry Pi OS lite images create the user on first boot via
# cloud-init/imager; inside nspawn we do it ourselves.
if [ -d "$MNT/home/pi" ]; then
    echo "User pi already exists"
else
    echo "Creating user pi"
    chroot "$MNT" /usr/sbin/useradd --create-home --shell /bin/bash pi || true
fi
echo '%sudo ALL=(ALL) NOPASSWD:ALL' > "$MNT/etc/sudoers.d/waqd-os-test"
chmod 440 "$MNT/etc/sudoers.d/waqd-os-test"
if [ -x "$MNT/usr/sbin/usermod" ]; then
    chroot "$MNT" /usr/sbin/usermod -aG sudo pi || true
else
    echo "WARNING: $MNT/usr/sbin/usermod is unavailable; leaving existing groups unchanged" >&2
fi

# Bind-mount the repo so the installer runs from the working tree.
mkdir -p "$MNT/waqd"
if ! mountpoint -q "$MNT/waqd"; then
    echo "Bind-mounting $REPO at $MNT/waqd"
    mount --bind "$REPO" "$MNT/waqd"
fi

# --- boot it ----------------------------------------------------------------
# -b/--boot: run a real init. --bind: expose the repo inside the machine.
echo "Booting machine '$MACHINE'..."
echo "  Attach from another shell:  machinectl shell $MACHINE"
echo "  Stop and clean up:          machinectl poweroff $MACHINE && sudo $0 --cleanup $LOOP $MNT"

systemd-nspawn \
    --machine "$MACHINE" \
    --directory "$MNT" \
    --boot \
    --bind "$REPO:/waqd" \
    --setenv=PYTHONPATH=/waqd/src \
    --setenv=HOME=/home/pi \
    --setenv=USER=pi

# --- cleanup ----------------------------------------------------------------
echo "Machine stopped, cleaning up"
if [ "${WAQD_KEEP_MOUNT:-0}" = "1" ]; then
    echo "Keeping prepared rootfs at $MNT"
fi
echo "Done"
