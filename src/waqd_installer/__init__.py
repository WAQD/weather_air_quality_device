from pathlib import Path
import platform


""" TODO: This will switch paths or whole functions depending on the debian version to support
later versions and avoid problems when updating on old systems. 
Currently only trixie is supported, but this can be easily extended to support more versions.
"""


def debian_codename() -> str | None:
    path = "/etc/os-release"
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("VERSION_CODENAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except FileNotFoundError:
        return None
    return None


if debian_codename() == "trixie":
    from .trixie import AUTOSTART_FILE
elif platform.machine() in ("aarch64", "armv7l", "armv6l", "armv8l"):
    # on target hardware with an unsupported Debian version
    raise NotImplementedError(f"Unsupported Debian version: {debian_codename()}")
else:
    # non-target machine (dev/test): dummy setup
    AUTOSTART_FILE = Path("/tmp/dummy_autostart_file")

__all__ = ["AUTOSTART_FILE"]
