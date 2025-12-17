#!/bin/bash

### ENTRYPOINT OF UPDATER/INSTALLER! DON'T RENAME THIS FILE!

# read in flags
USE_ZENITY=true
for arg in "$@"; do
    if [ "$arg" == "--inverted_display" ]; then
        INVERTED_DISPLAY=--inverted_display
    elif [ "$arg" == "--no-gui" ]; then
        USE_ZENITY=false
    fi
done
export INVERTED_DISPLAY

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
SRC_DIR=${CURRENT_DIR}/../../src

chmod +x $CURRENT_DIR/exec_install.sh
. $CURRENT_DIR/exec_install.sh # start apt update and loads waqd_install func

if [ "$USE_ZENITY" = true ]; then
    # show update background screen
    feh -F -x $SRC_DIR/waqd/assets/gui_base/update_screen.png &

    # start Updater function and pass output to zenity. Echos starting with '#' wil be visible in the dialog.
    # Pulsating means, that we have a bouncing loading bar, without actually displaying progress.
    export GTK_A11Y=none
    waqd_install 2>&1 | tee ~/.waqd/install_details.log | zenity --progress --pulsate --width 250 --no-cancel --title "Updating..." --auto-close &

    # move the window between the text on the background image (src\waqd\assets\gui_base\update_screen.png)
    if timeout 1s xset q &>/dev/null; then # only if xserver is running
        # wait until there is a window
        NEXT_WAIT_TIME=0
        until [ $NEXT_WAIT_TIME -eq 50 ] || [[ $(wmctrl -lp | grep $(pidof zenity) | cut -d' ' -f1) ]]
        do
            sleep 0.1
            let NEXT_WAIT_TIME=NEXT_WAIT_TIME+1
        done
        xdotool windowmove $(wmctrl -lp | grep $(pidof zenity) | cut -d' ' -f1) 260 190
    fi
else
    # run installer directly without GUI
    waqd_install 2>&1
fi
