# OS-level install/update tests

Verifies that the system still works after an install **or an update**, by
running the real installer inside a throwaway OS and then asserting on the
resulting system state.

The installer is **Debian-specific, not architecture-specific**. Of its ~20 OS
modifications only 3 need real Pi hardware (`raspi-config`,
`/boot/firmware/config.txt`, plymouth initrd). Everything else — LXDE
autostart, lightdm, udev, ufw, `apt.conf.d`, pipx, systemd user units, pcmanfm
— is plain Debian. So there are two tiers:

| Tier | System | Speed | Covers | Needs |
|---|---|---|---|---|
| 1 | `debian:trixie-slim` container, x64 | minutes | ~85% of the install surface | docker |
| 2 | **official** Raspberry Pi OS image via `systemd-nspawn --boot` | slow (qemu on x64) | 100%, incl. real reboot | root, `losetup`, `systemd-nspawn` |

## Design: mutator and verifier are separate

The installer runs *inside* the system under test. Assertions run from
*outside* via `probe.py` — a stdlib-only script copied into the system. It
needs no project dependencies, so it works on a bare image and can be reused
across both tiers and on real hardware.

## Running

Everything here is skipped unless `WAQD_OS_TEST=1` is set (same gating pattern
as `WAQD_HW_CONNECTED` in `test/waqd_station/hardware/`).

### Local development fast lane

For local development, use the helper script instead of manually fetching an
image, starting nspawn, and launching pytest:

```fish
./script/os_test/dev_os_test.sh debian
./script/os_test/dev_os_test.sh rpios
```

The helper refuses to run when `CI=1` or `GITHUB_ACTIONS` is set. It reuses all
available caches, starts the RPi nspawn machine in the background, waits for it
to become available, runs the consolidated test, and cleans up the machine on
exit. The nspawn output is written to `/tmp/waqd-os-test-nspawn.log` by
default. Additional arguments are passed through to pytest.

Useful overrides include:

```fish
WAQD_OS_TEST_REBUILD=1 ./script/os_test/dev_os_test.sh debian
RPIOS_REFRESH=1 ./script/os_test/dev_os_test.sh rpios
WAQD_OS_TEST_SKIP_INSTALL=1 ./script/os_test/dev_os_test.sh rpios
```

### Tier 1 (Debian trixie)

```fish
source .venv/bin/activate.fish
WAQD_OS_TEST=1 python -m pytest test/os_test/test_install_debian.py -q --timeout=1800
```

Builds `test/os_test/Dockerfile.debian-trixie`, runs
`script/installer/start_installer.sh --no-gui` inside it, then probes. Also
tests **idempotency** (a second install must not duplicate entries) and the
**upgrade path** (N → N+1 must re-point autostart at the new binary).

### Tier 2 (official Raspberry Pi OS image)

```fish
# 1. get the official desktop image (downloads from downloads.raspberrypi.org,
#    verifies SHA-256, and caches the resolved image path)
./script/os_test/fetch_rpios_image.sh

# 2. boot it - needs root, keeps running in the foreground
sudo ./script/os_test/run_nspawn.sh ~/.cache/waqd-os-test/<image>.img

# 3. in another shell
source .venv/bin/activate.fish
WAQD_OS_TEST=1 python -m pytest test/os_test/test_install_rpios.py -q --timeout=3600
```

The image fetch defaults to the official ARM64 desktop image and caches it in
`~/.cache/waqd-os-test/current-image`. Use `RPIOS_REFRESH=1` to resolve and
download again, or `RPIOS_URL=...` to select a specific official image.

To preserve a prepared root filesystem after nspawn exits, use a persistent
mount directory:

```fish
sudo WAQD_KEEP_MOUNT=1 WAQD_NSPAWN_MNT=/var/tmp/waqd-rpios-root \
  ./script/os_test/run_nspawn.sh ~/.cache/waqd-os-test/<image>.img
```

Subsequent boots can reuse that prepared mount with the same
`WAQD_NSPAWN_MNT` value. Set `WAQD_REFRESH=1` when the prepared filesystem
must be recreated. Set `WAQD_OS_TEST_SKIP_INSTALL=1` when running the pytest
test against an installation already present in the image.

No unofficial base image is used: `losetup --partscan` + `mount` exposes the
real rootfs, and `systemd-nspawn --boot` runs a genuine PID 1 — so the
installer's `reboot` restarts the container's init instead of the host. This is
the only tier that exercises the reboot for real, and it asserts the device
comes back with `waqd-start` respawned and the UI serving.

## The reboot problem

`exec_install.sh` ends with an unconditional `sudo reboot`, which is hostile to
testing. Two mechanisms handle it:

- `WAQD_SKIP_REBOOT=1` (or `--no-reboot`) writes `~/.waqd/reboot_requested`
  instead of rebooting. The probe asserts the marker exists, so the reboot is
  still verified — just not performed.
- Tier 2 doesn't need the flag: nspawn's real PID 1 makes `reboot` safe, and
  `test_device_comes_back_after_reboot` asserts the app respawns afterwards.

## Probe checks

`autostart`, `bin`, `pipx`, `lightdm`, `screensaver`, `udev`, `ufw`, `influx`,
`apt_conf`, `audio`, `splash`, `hw_access`, `desktop`, `reboot`, `runtime`.

`splash` and `hw_access` are skipped off-Pi; `desktop` needs a `DISPLAY`;
`runtime` needs the app running. Run one directly for debugging:

```fish
docker exec waqd-os-test-debian python3 /tmp/waqd_probe.py autostart bin --user pi
```

## PATH shims

The Tier 1 image installs shims in `/opt/waqd-shims` for `raspi-config`,
`plymouth-set-default-theme`, `reboot` and `shutdown`. Each logs to
`/var/log/waqd-shims.log` and exits 0, so the installer takes the same code
path as on a real device without failing — and the tests can assert it
*tried*.
