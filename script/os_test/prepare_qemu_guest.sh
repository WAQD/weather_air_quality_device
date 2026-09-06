#!/bin/bash
# Prepare a Raspberry Pi OS image for rootless QEMU SSH testing.
# This intentionally uses a copy of the image; it never mounts the user's image.
# Requires libguestfs tools and a writable copy of the official image. Guest
# commands are deliberately installed as a first-boot script: libguestfs
# cannot execute aarch64 binaries while running on this x86_64 host.
set -euo pipefail

IMG="${1:?usage: prepare_qemu_guest.sh <image> <public-key> <output-image>}"
PUBKEY="${2:?usage: prepare_qemu_guest.sh <image> <public-key> <output-image>}"
OUT="${3:?usage: prepare_qemu_guest.sh <image> <public-key> <output-image>}"

for tool in qemu-img virt-customize; do
    command -v "$tool" >/dev/null || { echo "ERROR: $tool is required" >&2; exit 2; }
done
qemu-img convert -O raw "$IMG" "$OUT"
FIRSTBOOT=$(mktemp)
trap 'rm -f "$FIRSTBOOT"' EXIT
cat > "$FIRSTBOOT" <<'EOF'
#!/bin/bash
set -eu
id pi >/dev/null 2>&1 || useradd --create-home --shell /bin/bash pi
usermod -aG sudo pi || true
mkdir -p /home/pi/.ssh
cp /tmp/waqd-qemu-authorized_keys /home/pi/.ssh/authorized_keys
chown -R pi:pi /home/pi/.ssh
chmod 700 /home/pi/.ssh
chmod 600 /home/pi/.ssh/authorized_keys
printf '%s\n' 'pi ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/waqd-os-test
chmod 440 /etc/sudoers.d/waqd-os-test
systemctl enable ssh || systemctl enable ssh.service || true
rm -f /etc/systemd/system/waqd-qemu-firstboot.service
EOF
chmod 755 "$FIRSTBOOT"
virt-customize -a "$OUT" \
    --upload "$PUBKEY:/tmp/waqd-qemu-authorized_keys" \
    --firstboot "$FIRSTBOOT"
