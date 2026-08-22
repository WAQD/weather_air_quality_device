#!/bin/python3
# This module runs as the normal user (NOT via sudo). It needs the desktop
# manager running and must not be run as root.

import logging
import os
from pathlib import Path
from configparser import ConfigParser, DuplicateSectionError

from waqd_installer.common import (
    HOME,
    assure_file_exists,
    rotate_and_overwrite_image,
)


def set_wallpaper(install_path: Path, inverted_display=False):
    # Can't be run as sudo, or as sudo -runuser. Needs desktop manager running.
    # set wallpaper - get image from install dir
    lib_paths = (install_path / "lib").iterdir()  # TODO does not work anymore
    for lib_path in lib_paths:
        if "python" in lib_path.name:
            image = lib_path / "site-packages/waqd_assets/gui_base/pre_loading_screen.png"
            if inverted_display:
                rotate_and_overwrite_image(image, 180)
            try:
                logging.info("Setting wallpaper..." + f'pcmanfm --set-wallpaper="{str(image)}"')
                os.system(f'pcmanfm --set-wallpaper="{str(image)}"')
            except Exception as e:
                logging.error(str(e))
            break


def clean_lxde_desktop(
    desktop_conf_path=Path(HOME / ".config/pcmanfm/default/desktop-items-0.conf"),
):
    # Can't be run as sudo, or as sudo -runuser. Needs desktop manager running.
    logging.info("Cleanup desktop icons... from " + str(desktop_conf_path))

    # Kill pcmanfm to prevent it from overwriting our changes
    os.system("pkill -f 'pcmanfm-pi' || true")

    assure_file_exists(desktop_conf_path)
    # needs to be under *
    cp = ConfigParser()
    with open(desktop_conf_path, "r", encoding="UTF-8") as fd:
        cp.read_file(fd)
    try:
        cp.add_section("*")
    except DuplicateSectionError:
        pass  # don't care
    cp["*"]["show_trash"] = "0"
    cp["*"]["show_mounts"] = "0"
    with open(desktop_conf_path, "w", encoding="UTF-8") as fd:
        cp.write(fd, space_around_delimiters=False)

    # Restart pcmanfm desktop to apply changes
    os.system("pcmanfm-pi </dev/null &>/dev/null &")
