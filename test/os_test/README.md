— is plain Debian. So there are two tiers:
# OS-level install/update tests

The tests verify the real installer in throwaway operating systems. Tier 1
uses a native Debian container. Tier 2 uses the official Raspberry Pi OS
ARM64 image in an isolated QEMU VM.

The host never mounts the Raspberry Pi image. Pytest creates a disposable qcow2
overlay, starts QEMU, communicates over SSH, performs the guest reboot, and
deletes the overlay on exit.

## Tiers

| Tier | Runtime | Coverage | Privileges |
|---|---|---|---|
| 1 | Rootless Podman/Docker, Debian Trixie | Installer and update behavior | Container runtime only |
| 2 | QEMU ARM64 VM, official Raspberry Pi OS | Pi-specific checks and reboot | None on host |

## Tier 1

```fish
./script/os_test/dev_os_test.sh debian
```

## Tier 2 requirements

- `qemu-system-aarch64`, `qemu-img`
- `ssh`, `scp`, and `ssh-keygen`
- A prepared guest image containing user `pi`, SSH, and the test public key

The host does not need sudo, loop devices, `systemd-nspawn`, `machinectl`, or
ARM64 binfmt registration.

## Preparing and running Tier 2

Run the setup script with a compatible ARM64 kernel. It creates the dedicated
test key, fetches the official image if necessary, prepares a writable copy,
and writes environment files for Fish and Bash:

```fish
./script/os_test/setup_qemu.sh --kernel /path/to/arm64-kernel.img
source ~/.cache/waqd-os-test/qemu-env.fish
./script/os_test/dev_os_test.sh rpios
```

The equivalent Bash setup is:

```bash
./script/os_test/setup_qemu.sh --kernel /path/to/arm64-kernel.img
source ~/.cache/waqd-os-test/qemu-env.sh
./script/os_test/dev_os_test.sh rpios
```

Use `--force` to regenerate the key and prepared image.

The same variables can be used with pytest directly:

```bash
WAQD_RPIOS_IMAGE=/path/to/prepared.img \
WAQD_QEMU_SSH_KEY=/path/to/id_ed25519 \
WAQD_OS_TEST=1 pdm run pytest test/os_test/test_install_rpios.py -s --timeout=3600
```

The setup extracts `kernel8.img` from the official image and QEMU boots it with
the `raspi3b` machine model. `WAQD_QEMU_APPEND` overrides the kernel command
line. The default is:

```text
root=/dev/vda2 rw rootwait console=ttyAMA0,115200 systemd.unit=multi-user.target
```

`script/os_test/run_qemu.sh` creates a qcow2 copy-on-write overlay for each
run and removes it on exit. The official base image remains unchanged.
