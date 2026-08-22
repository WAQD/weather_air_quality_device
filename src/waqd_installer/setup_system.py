#!/bin/python3
# This script is being run as admin!

import logging
import os
import shutil
from pathlib import Path

from waqd_installer.common import (
    HOME,
    add_line_to_file,
    assure_file_exists,
    installer_root_dir,
    add_to_LXDE_autostart,
    remove_from_autostart,
    remove_line_in_file,
    rotate_and_overwrite_image,
)
from waqd_installer import AUTOSTART_FILE


def disable_screensaver():
    logging.info("Check the screensaver")

    config_file = HOME / ".xscreensaver"
    switch_off_cmd = "mode: off\n"
    assure_file_exists(config_file, chown=False)
    logging.info("Disabling screen saver.")
    remove_line_in_file(["mode:"], config_file)
    add_line_to_file([switch_off_cmd], config_file)
    logging.info("Add the screensaver to autostart")
    add_to_LXDE_autostart(AUTOSTART_FILE, ["xscreensaver -no-splash"])


def hide_mouse_cursor():
    """Modify xserver-command to append -nocursor"""
    lightdm_config_file = Path("/usr/share/lightdm/lightdm.conf.d/01_debian.conf")
    assure_file_exists(lightdm_config_file, chown=False)
    logging.info("Hiding mouse cursor")
    remove_line_in_file(["xserver-command"], lightdm_config_file)
    add_line_to_file(["xserver-command=X -nocursor"], lightdm_config_file)


def enable_hw_access():
    # enable non-sudo usage of rpi-backlight
    rules_dir = "/etc/udev/rules.d"
    rules_file = "backlight-permissions.rules"
    rules_path = Path(rules_dir) / rules_file
    assure_file_exists(rules_path, chown=False)
    enable_text = (
        'SUBSYSTEM=="backlight",RUN+="/bin/chmod 666 /sys/class/backlight/%k/brightness'
        ' /sys/class/backlight/%k/bl_power"'
    )
    add_line_to_file([enable_text], rules_path, unique=True)


def customize_splash_screen(inverted_display: bool):
    # copy splash screen to /usr/share/plymouth/themes/pix
    os.makedirs("/usr/share/plymouth/themes/pix", exist_ok=True)
    try:
        logging.info("Customizing splash screen")
        src_image = f"{str(installer_root_dir)}/src/waqd_assets/gui_base/loading_screen.png"
        if inverted_display:
            rotate_and_overwrite_image(src_image, 180)
        shutil.copy(src_image, "/usr/share/plymouth/themes/pix/splash.png")
        # remove rainbow screen
        os.system(
            "raspi-config nonint set_config_var disable_splash 1 /boot/firmware/config.txt"
        )
        os.system("sudo plymouth-set-default-theme --rebuild-initrd pix")
    except Exception as e:
        logging.error(str(e))


def do_setup(inverted_dislplay: bool):
    # System setup
    # Start only the desktop, but not the taskbar
    add_to_LXDE_autostart(AUTOSTART_FILE, ["pcmanfm-pi"])
    remove_from_autostart(AUTOSTART_FILE, ["lxpanel-pi"])

    hide_mouse_cursor()
    disable_screensaver()

    # Cosmetic setup
    customize_splash_screen(inverted_dislplay)

    # Enable needed hardware access
    enable_hw_access()


def configure_unnattended_updates(
    auto_updates_path=Path("/etc/apt/apt.conf.d/20auto-upgrades"),
    unattended_updates_path=Path("/etc/apt/apt.conf.d/50unattended-upgrades"),
):
    # enable apt update and the unattended updates feature
    remove_line_in_file(
        ["APT::Periodic::Update-Package-Lists", "APT::Periodic::Unattended-Upgrade"],
        auto_updates_path,
    )
    add_line_to_file(
        ['APT::Periodic::Update-Package-Lists "1";', 'APT::Periodic::Unattended-Upgrade "1";'],
        auto_updates_path,
    )

    # configure update mechanism
    remove_line_in_file(
        [
            "Unattended-Upgrade::Remove-Unused-Dependencies",
            "Unattended-Upgrade::AutoFixInterruptedDpkg",
            "Unattended-Upgrade::MinimalSteps",
        ],
        unattended_updates_path,
    )
    add_line_to_file(
        [
            # we have enough space, we don't know what pkgs are removed -> safety
            'Unattended-Upgrade::Remove-Unused-Dependencies "false";',
            # try to repair if somehow update was interrupted
            'Unattended-Upgrade::AutoFixInterruptedDpkg "true";',
            # use minimal steps to have the lowest possible rate of failure if update is interrupted
            'Unattended-Upgrade::MinimalSteps "true"',
        ],
        unattended_updates_path,
    )
