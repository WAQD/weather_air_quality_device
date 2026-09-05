#!/bin/python3
# This script is being run as admin!

import logging
import os
import stat
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from . import AUTOSTART_FILE
from .common import (
    INSTALL_TARGET_ROOT, INSTALL_DIR_SUFFIX, LOCAL_BIN_PATH, USERNAME,
    installer_root_dir,
    add_to_LXDE_autostart, get_waqd_version, get_waqd_bin_name, remove_from_autostart, set_write_permissions, setup_logger)

def install_waqd(waqd_version: str):
    logging.info("Installing with pipx")
    # use system-site-packages to use qt system package
    # -- suffix creates a version specific dir. "." will be converted to "-" in the name
    suffix = INSTALL_DIR_SUFFIX.format(version=waqd_version)
    # must be executed as user
    args = f"--force --verbose --system-site-packages --suffix {suffix} {installer_root_dir}[waqd]"
    install_cmd = f'runuser - {USERNAME} -c "python3 -m pipx install {args}"'
    logging.info(install_cmd)
    if os.system(install_cmd) != 0:
        raise RuntimeError(f"Failed to install waqd with pipx: {install_cmd}")
    
    # Remove RPi.GPIO installed by mh_z19 to allow rpi-lgpio from system site-packages to work
    # rpi-lgpio provides RPi.GPIO compatibility but gets shadowed if RPi.GPIO is installed
    waqd_bin_name = get_waqd_bin_name()
    uninstall_cmd = f'runuser - {USERNAME} -c "python3 -m pipx runpip {waqd_bin_name} uninstall -y RPi.GPIO"'
    logging.info(f"Removing conflicting RPi.GPIO package: {uninstall_cmd}")
    if os.system(uninstall_cmd) != 0:
        raise RuntimeError(f"Failed to remove conflicting RPi.GPIO: {uninstall_cmd}")

def register_waqd_autostart(autostart_file: Path, bin_path: Path = LOCAL_BIN_PATH):
    # Create an executable with auto restart for the current user
    # TODO: This would be nicer? with systemctl -> Restart=on-failure..
    os.makedirs(bin_path, exist_ok=True)
    
    waqd_start_bin_path = bin_path / "waqd-start"
    waqd_bin_name = get_waqd_bin_name()
    waqd_bin_content = f"""#!/bin/bash
    until {waqd_bin_name}; do
        echo "WAQD crashed with exit code $?.  Respawning.." >&2
        sleep 1
    done
    """
    with open(waqd_start_bin_path, "w", encoding="utf-8") as fd:
        fd.write(waqd_bin_content)
    # chmod +x
    os.chmod(waqd_start_bin_path, os.stat(waqd_start_bin_path).st_mode | stat.S_IEXEC)
    os.system(f"chown {USERNAME} {waqd_start_bin_path}")
    logging.info(f"Add respawning {str(waqd_start_bin_path)} to autostart file {str(autostart_file)}")
    # first remove, to not aciddentally remove added lines
    remove_from_autostart(
        autostart_file,
        ["waqd", "PiWeather"],
    )
    add_to_LXDE_autostart(
        autostart_file,
        [str(waqd_start_bin_path)],
    )

def do_install():
    # install and add to autostart
    set_write_permissions(INSTALL_TARGET_ROOT)
    version = get_waqd_version()
    logging.info(f"Installing version {version} of waqd")
    install_waqd(version)

    register_waqd_autostart(AUTOSTART_FILE)