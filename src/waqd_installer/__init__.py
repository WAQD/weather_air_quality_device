from pathlib import Path


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
else:
    # dummy setup:
    AUTOSTART_FILE = Path("/tmp/dummy_autostart_file")

__all__ = ["AUTOSTART_FILE"]