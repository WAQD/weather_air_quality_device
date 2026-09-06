# Isolated Raspberry Pi OS test runtime

The RPi OS tier uses QEMU instead of systemd-nspawn. The official image is
never mounted by the host. Pytest creates a disposable qcow2 overlay, starts an
ARM64 VM, communicates over SSH, performs the real guest reboot, and deletes
the overlay when the test exits.

## Prerequisites

Install:

- `qemu-system-aarch64`
- `qemu-img`
- `virt-customize` from the Arch `guestfs-tools` package
- `openssh-client`
- a prepared guest image containing `pi`, SSH, and the test public key

The host does not need sudo, loop devices, `systemd-nspawn`, `machinectl`, or
ARM64 binfmt registration.

Guest provisioning uses a first-boot script because the host is x86_64 while
the official guest image is AArch64; no guest commands are executed by
libguestfs during image preparation. The setup mounts the image partitions
internally through libguestfs and extracts `kernel8.img` from the separate FAT
boot partition in that same official image.

## Running

```bash
WAQD_RPIOS_IMAGE=$HOME/.cache/waqd-os-test/2026-06-18-raspios-trixie-arm64.img \
WAQD_OS_TEST=1 pdm run pytest test/os_test/test_install_rpios.py -s --timeout=3600
```

The fast lane is:

```bash
./script/os_test/dev_os_test.sh rpios
```

`WAQD_QEMU_APPEND` can override the kernel command line. The default is:

```text
root=/dev/vda2 rw rootwait console=ttyAMA0,115200 systemd.unit=multi-user.target
```

## Guest preparation

If `libguestfs` is available, prepare a disposable bootable copy with:

```bash
./script/os_test/prepare_qemu_guest.sh base.img id_ed25519.pub prepared.img
```

This configures SSH, user `pi`, and passwordless sudo in the copy. The base
official image remains unchanged.

The launcher itself is `script/os_test/run_qemu.sh`. It creates a qcow2
copy-on-write overlay and removes it on exit.
