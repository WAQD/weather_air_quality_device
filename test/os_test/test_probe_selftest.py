"""Self-test for probe.py.

The probe is the verifier for every other test in this directory, so it needs
its own test — otherwise a probe that always fails (or always passes) would
silently invalidate the whole suite.

It builds a fake "installed" tree under a temp dir and asserts the probe
reports PASS for it, then asserts it reports FAIL for an empty tree. This runs
on the host with no docker/root, so it is NOT gated by WAQD_OS_TEST.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROBE = Path(__file__).parent / "probe.py"
VERSION = "3.2.0"


def _run_probe(home: Path, checks=("all",), version=VERSION):
    env = {**os.environ, "WAQD_TEST_HOME": str(home)}
    proc = subprocess.run(
        [sys.executable, str(PROBE), *checks, "--user", "pi", "--version", version, "--json"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert proc.returncode in (0, 1), f"probe crashed:\n{proc.stdout}\n{proc.stderr}"
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    return summary, proc.stdout


@pytest.fixture
def fake_install(tmp_path):
    """Build a tree that looks exactly like a successful install."""
    home = tmp_path / "home"
    (home / ".config/lxsession/rpd-x").mkdir(parents=True)
    (home / ".config/pcmanfm/default").mkdir(parents=True)
    (home / ".config/systemd/user").mkdir(parents=True)
    (home / ".local/bin").mkdir(parents=True)
    (home / ".waqd").mkdir(parents=True)

    (home / ".config/lxsession/rpd-x/autostart").write_text(
        f"@pcmanfm-pi\n@xscreensaver -no-splash\n@{home / '.local/bin/waqd-start'}\n"
    )
    start = home / ".local/bin/waqd-start"
    start.write_text(f"#!/bin/bash\nuntil waqd.{VERSION}; do sleep 1; done\n")
    start.chmod(0o755)

    (home / ".xscreensaver").write_text("mode: off\n")
    (home / ".config/pcmanfm/default/desktop-items-0.conf").write_text(
        "[*]\nshow_trash=0\nshow_mounts=0\n"
    )
    (home / ".config/systemd/user/set-default-audio-volume.service").write_text(
        "[Service]\nExecStart=/usr/bin/pactl set-sink-volume @DEFAULT_SINK@ 100%\n"
    )
    (home / ".waqd/reboot_requested").write_text("2026-09-05T12:00:00Z\n")

    # pipx venv with RPi.GPIO absent
    venv = home / f".local/share/pipx/venvs/waqd-{VERSION.replace('.', '-')}"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin/python3").write_text("#!/bin/sh\nexit 1\n")  # import RPi.GPIO fails
    (venv / "bin/python3").chmod(0o755)

    return home


def test_probe_passes_on_a_correct_install(fake_install):
    summary, out = _run_probe(fake_install)
    # ufw/influx/udev/lightdm live outside $HOME and can't be faked here.
    expected_pass = {"autostart", "bin", "pipx", "screensaver", "audio", "desktop", "reboot"}
    assert expected_pass <= set(summary["passed"]), (
        f"expected {sorted(expected_pass)} to pass, but failed={summary['failed']}\n{out}"
    )
    assert not (expected_pass & set(summary["failed"]))


def test_probe_fails_on_an_empty_tree(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    summary, _ = _run_probe(empty)
    assert summary["failed"], "probe must report failures for an uninstalled system"
    for name in ("autostart", "bin", "pipx", "screensaver", "audio", "desktop", "reboot"):
        assert name in summary["failed"], f"{name} should have failed on an empty tree"


def test_probe_detects_duplicate_autostart_entries(fake_install):
    """Idempotency regression: a doubled waqd-start line must be caught."""
    autostart = fake_install / ".config/lxsession/rpd-x/autostart"
    lines = autostart.read_text().splitlines()
    autostart.write_text("\n".join(lines + [lines[-1]]) + "\n")
    summary, out = _run_probe(fake_install, checks=("autostart",))
    assert "autostart" in summary["failed"], f"duplicate not detected:\n{out}"


def test_probe_detects_stale_lxpanel(fake_install):
    """The installer removes lxpanel-pi; the probe must catch it coming back."""
    autostart = fake_install / ".config/lxsession/rpd-x/autostart"
    autostart.write_text(autostart.read_text() + "@lxpanel-pi\n")
    summary, out = _run_probe(fake_install, checks=("autostart",))
    assert "autostart" in summary["failed"], f"lxpanel not detected:\n{out}"


def test_probe_detects_wrong_version(fake_install):
    """Autostart must point at the version being installed."""
    summary, out = _run_probe(fake_install, checks=("bin",), version="9.9.9")
    assert "bin" in summary["failed"], f"version mismatch not detected:\n{out}"


def test_probe_detects_rpi_gpio_still_present(fake_install):
    """RPi.GPIO must be uninstalled so rpi-lgpio from system site-packages wins."""
    venv = fake_install / f".local/share/pipx/venvs/waqd-{VERSION.replace('.', '-')}"
    (venv / "bin/python3").write_text("#!/bin/sh\nexit 0\n")  # import RPi.GPIO succeeds
    (venv / "bin/python3").chmod(0o755)
    summary, out = _run_probe(fake_install, checks=("pipx",))
    assert "pipx" in summary["failed"], f"RPi.GPIO not detected:\n{out}"
