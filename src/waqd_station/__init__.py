from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path


PROG_NAME = "WAQD"

try:
    pkg_info = distribution(PROG_NAME)
    __version__ = pkg_info.version
    # format: repository, https://...
    REPO_URL = pkg_info.metadata.get("project-url", "").split(", ")[1]  # type: ignore
    AUTHOR = pkg_info.metadata.get("author", "")  # type: ignore
except PackageNotFoundError:  # pragma: no cover
    # For local usecases, when there is no distribution
    __version__ = "1.0.0"
    REPO_URL = ""
    AUTHOR = ""

HEADLESS_MODE = False
MIGRATE_SENSOR_LOGS = False

user_config_dir = Path().home() / ".waqd"
user_config_dir.mkdir(parents=True, exist_ok=True)