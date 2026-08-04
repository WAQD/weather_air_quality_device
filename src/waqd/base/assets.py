import json
from functools import lru_cache
from pathlib import Path

import waqd
from waqd.base.file_logger import Logger

TOC_FILE_NAME = "filetoc.json"


@lru_cache(maxsize=None)
def _load_asset_toc(ftoc_path: Path) -> dict:
    """Read and parse filetoc.json once per path; assets don't change at runtime."""
    if not ftoc_path.exists():
        return {}
    with open(ftoc_path, encoding="utf-8") as filetoc:
        return json.load(filetoc)


def get_asset_file_relative(rsc_file_path: Path) -> str:
    """
    Get a an indexed resource file from the specified path.
    The function expects a filetoc.json, with a mapping from id to filename in "filelist".
    An additional "filetype" an be specified for a default extension. (without the dot)
    No error is raised, the error is only logged.
    """
    return rsc_file_path.relative_to(waqd.assets_path).as_posix()


def get_asset_file(rsc_dir: str, rsc_id: str) -> Path:
    """
    Get a an indexed resource file from the specified path.
    The function expects a filetoc.json, with a mapping from id to filename in "filelist".
    An additional "filetype" an be specified for a default extension. (without the dot)
    No error is raised, the error is only logged.
    """

    if rsc_id == "dummy-pic":  # specal case for a dummy picture
        rsc_dir = "gui_base"
    # read filetoc.json
    rsc_path = waqd.assets_path / rsc_dir
    ftoc_path = rsc_path / TOC_FILE_NAME
    logger = Logger()

    content = _load_asset_toc(ftoc_path)
    if not content:
        logger.debug("Cannot find catalog file %s, fallback to real filename.", ftoc_path)
        file_name = rsc_id
    else:
        # get filetype and filelist
        filetype = content.get("filetype", "")
        filelist = content.get("filelist", {})

        file_name = filelist.get(rsc_id, "")
        if not file_name:
            logger.debug(
                "Cannot find resource id %s in catalog, fallback to real filename.",
                rsc_id,
            )
            file_name = rsc_id
        # append filetype, if applicable
        if filetype:
            file_name = file_name + "." + filetype

    rsc_file_path = rsc_path / file_name
    if not rsc_file_path.exists():
        logger.error("Cannot find resource file %s in %s", file_name, str(rsc_dir))
        return Path("NULL")

    return rsc_file_path
