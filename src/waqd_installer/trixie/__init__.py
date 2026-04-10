import os

from waqd_installer.common import HOME


AUTOSTART_FILE = HOME / ".config/lxsession/rpd-x/autostart"
AUTOSTART_FILE.parent.mkdir(parents=True, exist_ok=True)
# add write permissions to user
os.system(f"sudo chmod 777 -R {str(AUTOSTART_FILE.parent)}")
