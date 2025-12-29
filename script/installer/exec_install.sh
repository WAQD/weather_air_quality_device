#!/bin/bash
export DEBIAN_FRONTEND=noninteractive # don't ask questions during install
# set current directory to script directory
CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
SRC_DIR=${CURRENT_DIR}/../../src
echo "##### Start updater process #####" 

# additional args to not fail on wrong clock time and enable update to newer distro releases
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" update
echo "##### Install feh and zenity #####" 
# zenity for dialog and feh background screen - xdotool and wmctrl for x-window manipulation
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" feh zenity xdotool wmctrl
# assure desktop manager is running
pcmanfm --desktop --profile LXDE-pi </dev/null &>/dev/null &
# kill zenity - need exactly one proc for grep later
pkill zenity || true
# stop sensor db for possible update
sudo systemctl stop influxdb || true

echo "##### Starting installer #####" 

function waqd_install() {
    # kill all necessary running applications
    # kill the application itself
    pkill waqd || true
    pkill python3 || true
    pkill chromium || true

    echo "# Install needed system libraries... (Step 1/5)"
    # python dependencies
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" python3-venv xscreensaver network-manager pulseaudio-utils  unattended-upgrades
    # install pipx for venv based app creation
    python3 -m pip install --user pipx==1.7.1 pillow --break-system-packages
    python3 -m pipx ensurepath

    echo "# Full system update... (Step 2/5)"
    sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
    sudo DEBIAN_FRONTEND=noninteractive apt-get autoremove -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

    echo "# Installing InfluxDB Database... (Step 3/5)"
    cd $CURRENT_DIR
    chmod +x ./setup/install_influx.sh
    ./setup/install_influx.sh

    echo "# Setting up the system (Step 4/5)"

    chmod +x ./setup/setup_firewall.sh
    ./setup/setup_firewall.sh

    chmod +x ./setup/set_volume_to_max.sh
    ./setup/set_volume_to_max.sh

    # Enable HW access (serial, i2c and spi)
    
    sudo raspi-config nonint do_serial_hw 0 # console off, serial on
    sudo raspi-config nonint do_serial_cons 1
    sudo raspi-config nonint do_i2c 0
    sudo raspi-config nonint do_spi 0
    sudo raspi-config nonint do_squeekboard S3 # disable
    sudo raspi-config nonint do_wayland W1 # X11

    sudo PYTHONPATH=${SRC_DIR} python3 -m waqd_installer --setup_system $INVERTED_DISPLAY

    echo "# Installing application... (Step 5/5)"
    sudo PYTHONPATH=${SRC_DIR} python3 -m waqd_installer --install $INVERTED_DISPLAY
    # needs installed app
    export PYTHONPATH=${SRC_DIR}
    python3 -m waqd_installer --set_wallpaper $INVERTED_DISPLAY
    
    echo "# Waiting for restart..."
    sudo reboot
}