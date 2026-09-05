#!/usr/bin/env python3
"""
Standalone verifier for a WAQD installation.

Runs *inside* the system under test (container, nspawn, or real device) and
asserts that the installer left the OS in the expected state. Deliberately
stdlib-only: it must run on a bare Debian/Raspberry Pi OS image that has no
project dependencies installed, and it must be copyable into a container
without any packaging.

Usage:
    probe.py all [--user pi] [--version 3.2.0]
    probe.py autostart bin pipx ...

Each check prints one line:  PASS <name> <detail>  or  FAIL <name> <detail>
Exit code is 0 only if every executed check passed.
"""

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

# Checks that only make sense on real Raspberry Pi hardware.
PI_ONLY = {"splash", "hw_access"}

# Checks that need a running desktop session / X server.
GUI_ONLY = {"desktop"}

# Checks that need the app to be running right now.
RUNTIME_ONLY = {"runtime"}

CHECKS = [
    "autostart",
    "bin",
    "pipx",
    "lightdm",
    "screensaver",
    "udev",
    "ufw",
    "influx",
    "apt_conf",
    "audio",
    "splash",
    "hw_access",
    "desktop",
    "reboot",
    "runtime",
]


class Result:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []

    def record(self, name, ok, detail="", skipped=False):
        if skipped:
            self.skipped.append(name)
            print(f"SKIP {name} {detail}".rstrip())
        elif ok:
            self.passed.append(name)
            print(f"PASS {name} {detail}".rstrip())
        else:
            self.failed.append(name)
            print(f"FAIL {name} {detail}".rstrip())

    @property
    def ok(self):
        return not self.failed


def _home(user):
    # WAQD_TEST_HOME lets the probe be self-tested against a fake tree without
    # installing anything on the host.
    override = os.environ.get("WAQD_TEST_HOME")
    if override:
        return Path(override)
    if user == "root":
        return Path("/root")
    return Path("/home") / user


def _run(cmd, **kwargs):
    """Run a command, return (returncode, stdout, stderr). Never raises."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            **kwargs,  # noqa: S603
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (OSError, subprocess.SubprocessError) as e:
        return 127, "", str(e)


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _count_occurrences(text, needle):
    return sum(1 for line in text.splitlines() if needle in line)


# --------------------------------------------------------------------------
# individual checks
# --------------------------------------------------------------------------


def check_autostart(res, home, version, **_kw):
    """LXDE autostart must have pcmanfm-pi + xscreensaver + waqd-start, no lxpanel."""
    path = home / ".config/lxsession/rpd-x/autostart"
    if not path.is_file():
        res.record("autostart", False, f"missing {path}")
        return
    text = _read(path)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    problems = []
    if not any("pcmanfm-pi" in ln for ln in lines):
        problems.append("no @pcmanfm-pi")
    if any("lxpanel" in ln for ln in lines):
        problems.append("lxpanel still present")
    if not any("xscreensaver" in ln for ln in lines):
        problems.append("no @xscreensaver")

    waqd_lines = [ln for ln in lines if "waqd-start" in ln]
    if len(waqd_lines) != 1:
        problems.append(f"expected exactly 1 waqd-start line, got {len(waqd_lines)}")
    elif not waqd_lines[0].startswith("@"):
        problems.append(f"waqd-start line not prefixed with @: {waqd_lines[0]!r}")

    # leftovers from older installs must be gone
    for stale in ("PiWeather",):
        if any(stale in ln for ln in lines):
            problems.append(f"stale entry {stale!r} present")

    # idempotency: no duplicated entries at all
    seen = [ln for ln in lines if lines.count(ln) > 1]
    if seen:
        problems.append(f"duplicate autostart lines: {sorted(set(seen))}")

    res.record("autostart", not problems, "; ".join(problems) or f"{len(lines)} lines")


def check_bin(res, home, version, **_kw):
    """~/.local/bin/waqd-start must exist, be executable, owned by the user."""
    path = home / ".local/bin/waqd-start"
    if not path.is_file():
        res.record("bin", False, f"missing {path}")
        return
    problems = []
    mode = path.stat().st_mode
    if not mode & stat.S_IXUSR:
        problems.append("not executable")
    content = _read(path)
    if "waqd" not in content:
        problems.append("does not reference waqd binary")
    if "until" not in content:
        problems.append("no respawn loop ('until')")
    if version and f"waqd.{version}" not in content:
        problems.append(f"does not reference waqd.{version}")
    res.record("bin", not problems, "; ".join(problems) or str(path))


def check_pipx(res, home, version, **_kw):
    """pipx venv for the version must exist and RPi.GPIO must be uninstalled."""
    problems = []
    venvs_dir = home / ".local/share/pipx/venvs"
    if version:
        expected = "waqd-" + version.replace(".", "-")
        venv = venvs_dir / expected
        if not venv.is_dir():
            problems.append(f"missing venv {venv}")
            res.record("pipx", False, "; ".join(problems))
            return
        # RPi.GPIO must be gone so rpi-lgpio from system site-packages wins
        python = venv / "bin/python3"
        if python.is_file():
            rc, out, _ = _run([str(python), "-c", "import RPi.GPIO"])
            if rc == 0:
                problems.append("RPi.GPIO still importable (shadows rpi-lgpio)")
        else:
            problems.append(f"no python in {venv}")
    else:
        if not venvs_dir.is_dir() or not any(venvs_dir.glob("waqd-*")):
            problems.append(f"no waqd venv under {venvs_dir}")
    res.record("pipx", not problems, "; ".join(problems) or "venv ok")


def check_lightdm(res, **_kw):
    """Mouse cursor must be hidden via lightdm xserver-command, exactly once."""
    path = Path("/usr/share/lightdm/lightdm.conf.d/01_debian.conf")
    if not path.is_file():
        res.record("lightdm", False, f"missing {path}")
        return
    text = _read(path)
    count = _count_occurrences(text, "xserver-command")
    problems = []
    if count == 0:
        problems.append("no xserver-command")
    elif count > 1:
        problems.append(f"xserver-command appears {count}x (not idempotent)")
    if "xserver-command=X -nocursor" not in text:
        problems.append("xserver-command is not 'X -nocursor'")
    res.record("lightdm", not problems, "; ".join(problems) or "cursor hidden")


def check_screensaver(res, home, **_kw):
    """~/.xscreensaver must have 'mode: off', exactly once."""
    path = home / ".xscreensaver"
    if not path.is_file():
        res.record("screensaver", False, f"missing {path}")
        return
    text = _read(path)
    count = _count_occurrences(text, "mode:")
    problems = []
    if "mode: off" not in text:
        problems.append("no 'mode: off'")
    if count > 1:
        problems.append(f"'mode:' appears {count}x (not idempotent)")
    res.record("screensaver", not problems, "; ".join(problems) or "disabled")


def check_udev(res, **_kw):
    """Backlight udev rule must grant non-root brightness write access."""
    path = Path("/etc/udev/rules.d/backlight-permissions.rules")
    if not path.is_file():
        res.record("udev", False, f"missing {path}")
        return
    text = _read(path)
    problems = []
    if 'SUBSYSTEM=="backlight"' not in text:
        problems.append("no backlight SUBSYSTEM match")
    if "chmod 666" not in text:
        problems.append("no chmod 666")
    if "/sys/class/backlight/" not in text:
        problems.append("no /sys/class/backlight path")
    res.record("udev", not problems, "; ".join(problems) or "rule present")


def check_ufw(res, **_kw):
    """Firewall must be active with the expected ports open."""
    if not shutil.which("ufw"):
        res.record("ufw", False, "ufw not installed")
        return
    rc, out, _ = _run(["ufw", "status", "verbose"])
    if rc != 0:
        res.record("ufw", False, f"ufw status failed: {out.strip()}")
        return
    problems = []
    if "Status: active" not in out:
        problems.append("ufw not active")
    for port in ("22", "5900", "80", "443", "53", "67"):
        if not re.search(rf"\b{port}\b.*ALLOW", out):
            problems.append(f"port {port} not allowed")
    res.record("ufw", not problems, "; ".join(problems) or "active, ports open")


def check_influx(res, **_kw):
    """InfluxDB must be installed (sensor history backend)."""
    rc, out, _ = _run(["dpkg-query", "-W", "-f=${Status}", "influxdb2"])
    installed = rc == 0 and "install ok installed" in out
    if not installed:
        # fall back to a bare binary check
        installed = shutil.which("influxd") is not None
    res.record("influx", installed, "influxdb2 installed" if installed else "not installed")


def check_apt_conf(res, **_kw):
    """Unattended-upgrades must be enabled and configured."""
    problems = []
    auto = Path("/etc/apt/apt.conf.d/20auto-upgrades")
    unatt = Path("/etc/apt/apt.conf.d/50unattended-upgrades")
    if not auto.is_file():
        problems.append(f"missing {auto}")
    else:
        text = _read(auto)
        for key in ("APT::Periodic::Update-Package-Lists", "APT::Periodic::Unattended-Upgrade"):
            if not re.search(rf'{re.escape(key)}\s+"1"', text):
                problems.append(f"{key} not enabled")
            if _count_occurrences(text, key) > 1:
                problems.append(f"{key} duplicated (not idempotent)")
    if not unatt.is_file():
        problems.append(f"missing {unatt}")
    else:
        text = _read(unatt)
        for key, val in (
            ("Unattended-Upgrade::Remove-Unused-Dependencies", "false"),
            ("Unattended-Upgrade::AutoFixInterruptedDpkg", "true"),
            ("Unattended-Upgrade::MinimalSteps", "true"),
        ):
            if not re.search(rf'{re.escape(key)}\s+"{val}"', text):
                problems.append(f"{key} != {val}")
            if _count_occurrences(text, key) > 1:
                problems.append(f"{key} duplicated (not idempotent)")
    res.record("apt_conf", not problems, "; ".join(problems) or "configured")


def check_audio(res, home, **_kw):
    """User systemd unit must set the default sink volume to 100%."""
    path = home / ".config/systemd/user/set-default-audio-volume.service"
    if not path.is_file():
        res.record("audio", False, f"missing {path}")
        return
    text = _read(path)
    problems = []
    if "set-sink-volume" not in text:
        problems.append("no set-sink-volume")
    if "100%" not in text:
        problems.append("volume not 100%")
    res.record("audio", not problems, "; ".join(problems) or "unit present")


def check_splash(res, **_kw):
    """Plymouth splash + disabled rainbow screen (Pi only)."""
    problems = []
    splash = Path("/usr/share/plymouth/themes/pix/splash.png")
    if not splash.is_file():
        problems.append(f"missing {splash}")
    cfg = Path("/boot/firmware/config.txt")
    if cfg.is_file():
        if "disable_splash=1" not in _read(cfg):
            problems.append("disable_splash not set in config.txt")
    res.record("splash", not problems, "; ".join(problems) or "splash customized")


def check_hw_access(res, **_kw):
    """raspi-config must have enabled serial/i2c/spi (Pi only)."""
    problems = []
    cfg = Path("/boot/firmware/config.txt")
    if not cfg.is_file():
        res.record("hw_access", False, "no /boot/firmware/config.txt")
        return
    text = _read(cfg).lower()
    for key in ("dtparam=i2c_arm=on", "dtparam=spi=on"):
        if key not in text:
            problems.append(f"{key} not set")
    res.record("hw_access", not problems, "; ".join(problems) or "i2c/spi enabled")


def check_desktop(res, home, **_kw):
    """pcmanfm desktop must hide trash and mounts."""
    path = home / ".config/pcmanfm/default/desktop-items-0.conf"
    if not path.is_file():
        res.record("desktop", False, f"missing {path}")
        return
    text = _read(path)
    problems = []
    if not re.search(r"show_trash\s*=\s*0", text):
        problems.append("show_trash != 0")
    if not re.search(r"show_mounts\s*=\s*0", text):
        problems.append("show_mounts != 0")
    res.record("desktop", not problems, "; ".join(problems) or "desktop cleaned")


def check_reboot(res, home, **_kw):
    """Installer must have requested a reboot (marker written when skipped)."""
    marker = home / ".waqd/reboot_requested"
    res.record(
        "reboot",
        marker.is_file(),
        f"marker {marker}" if marker.is_file() else f"no reboot marker at {marker}",
    )


def check_runtime(res, **_kw):
    """The app must be running and serving the UI + API."""
    problems = []
    rc, out, _ = _run(["pgrep", "-f", "waqd-start"])
    if rc != 0 or not out.strip():
        problems.append("waqd-start process not running")

    for url in (
        "http://localhost:8080/weather",
        "http://localhost:8080/api/sensor/v1/interior",
    ):
        if shutil.which("curl"):
            rc, out, _ = _run(["curl", "-sf", "-o", "/dev/null", "-w", "%{http_code}", url])
            if rc != 0 or out.strip() != "200":
                problems.append(f"{url} -> {out.strip() or 'unreachable'}")
        else:
            problems.append("curl not available")
            break

    log = Path(os.path.expanduser("~")) / ".waqd/waqd.log"
    if log.is_file():
        if "Traceback" in _read(log):
            problems.append("Traceback found in waqd.log")
    res.record("runtime", not problems, "; ".join(problems) or "app running, UI+API 200")


CHECK_FUNCS = {
    "autostart": check_autostart,
    "bin": check_bin,
    "pipx": check_pipx,
    "lightdm": check_lightdm,
    "screensaver": check_screensaver,
    "udev": check_udev,
    "ufw": check_ufw,
    "influx": check_influx,
    "apt_conf": check_apt_conf,
    "audio": check_audio,
    "splash": check_splash,
    "hw_access": check_hw_access,
    "desktop": check_desktop,
    "reboot": check_reboot,
    "runtime": check_runtime,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checks", nargs="+", choices=CHECKS + ["all"])
    parser.add_argument(
        "--user", default=os.environ.get("SUDO_USER") or os.environ.get("USER", "pi")
    )
    parser.add_argument("--version", default=os.environ.get("WAQD_VERSION", ""))
    parser.add_argument("--json", action="store_true", help="emit a JSON summary")
    args = parser.parse_args()

    names = CHECKS if "all" in args.checks else args.checks
    home = _home(args.user)
    res = Result()

    for name in names:
        func = CHECK_FUNCS[name]
        if name in PI_ONLY and not Path("/boot/firmware/config.txt").exists():
            res.record(name, True, skipped=True, detail="not a Raspberry Pi")
            continue
        if name in GUI_ONLY and not os.environ.get("DISPLAY"):
            res.record(name, True, skipped=True, detail="no DISPLAY")
            continue
        try:
            func(res, home=home, version=args.version)
        except Exception as e:  # a crashing check is a failing check
            res.record(name, False, f"check raised {type(e).__name__}: {e}")

    if args.json:
        print(
            json.dumps(
                {"passed": res.passed, "failed": res.failed, "skipped": res.skipped},
            )
        )
    else:
        print(
            f"\n{len(res.passed)} passed, {len(res.failed)} failed, {len(res.skipped)} skipped"
        )
    return 1 if res.failed else 0


if __name__ == "__main__":
    sys.exit(main())
