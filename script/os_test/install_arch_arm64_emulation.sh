#!/bin/bash
# Install ARM64 user-mode emulation on Arch Linux for the Raspberry Pi OS tests.
#
# This enables execution of the official ARM64 Raspberry Pi OS userspace through
# systemd-nspawn on an x86_64 Arch host. It does not emulate Raspberry Pi
# hardware; GPIO/SPI/I2C/display behavior still requires a real Pi.
#
# Usage:
#   sudo ./script/os_test/install_arch_arm64_emulation.sh
#
# Set WAQD_SKIP_REBOOT=1 to avoid rebooting after installing the binfmt rules.

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: run this script with sudo or as root." >&2
    exit 1
fi

if ! command -v pacman >/dev/null 2>&1; then
    echo "ERROR: this script supports Arch Linux only (pacman not found)." >&2
    exit 1
fi

if [ "$(uname -m)" = "aarch64" ] || [ "$(uname -m)" = "arm64" ]; then
    echo "Native ARM64 host detected; QEMU user emulation is unnecessary."
    exit 0
fi

echo "Installing QEMU ARM64 user-mode emulation and binfmt rules..."
pacman -Syu --needed qemu-user-static qemu-user-static-binfmt

# systemd-binfmt loads the package-provided rules from /usr/lib/binfmt.d.
if command -v systemctl >/dev/null 2>&1; then
    systemctl enable --now systemd-binfmt.service
    systemctl restart systemd-binfmt.service
fi

# Verify the actual interpreter and registration used by the test fixture.
if ! command -v qemu-aarch64-static >/dev/null 2>&1; then
    echo "ERROR: qemu-aarch64-static was not installed." >&2
    exit 1
fi

registered=0
for rule in /proc/sys/fs/binfmt_misc/qemu-aarch64 \
    /proc/sys/fs/binfmt_misc/arm64 \
    /proc/sys/fs/binfmt_misc/ARM64; do
    if [ -e "$rule" ]; then
        registered=1
        echo "ARM64 binfmt registered: $rule"
        break
    fi
done

if [ "$registered" -ne 1 ]; then
    echo "ERROR: ARM64 binfmt is not registered." >&2
    echo "Try: sudo systemctl restart systemd-binfmt.service" >&2
    exit 1
fi

echo "ARM64 emulation is ready for systemd-nspawn."
if [ "${WAQD_SKIP_REBOOT:-0}" != "1" ]; then
    echo "A reboot is recommended so binfmt registration is available early in boot."
fi
