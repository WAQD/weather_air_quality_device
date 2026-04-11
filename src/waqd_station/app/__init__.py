"""
Entry module of WAQD
Sets up cmd arguments, settings and starts the gui
"""

import sys
import time
from threading import Thread
from typing import TYPE_CHECKING

import waqd
import waqd_station
from waqd.base.assets import get_asset_file
from waqd.base.component_ctrl import ComponentController
from waqd.base.file_logger import Logger
from waqd.base.singleton import BorgSingleton
from waqd.base.system import RuntimeSystem
from waqd_station import MIGRATE_SENSOR_LOGS, user_config_dir
from waqd_station.settings import STARTUP_JINGLE, Settings

if TYPE_CHECKING:
    from waqd_station.app.component_reg import ComponentRegistry

# GLOBAL VARIABLES

unit_reg = waqd.unit_reg
# for global access to settings
settings = BorgSingleton(Settings, ini_folder=user_config_dir)

class CompCtrlSingleton(BorgSingleton[ComponentController["ComponentRegistry"]]):
    @classmethod
    def _create_instance(cls, key: object) -> ComponentController["ComponentRegistry"]:
        from waqd_station.app.component_reg import ComponentRegistry

        return ComponentController(settings(), ComponentRegistry)

# singleton with access to all backend components
comp_ctrl = CompCtrlSingleton()

def basic_setup():
    """
    Main function, calling setup, loading components and safe shutdown.
    :param settings_path: Only used for testing to load a settings file.
    """
    global comp_ctrl
    Logger(output_path=user_config_dir)  # singleton, no assigment needed

    sys.excepthook = crash_hook

    # to be able to remote debug as much as possible, this call is being done early
    start_remote_debug()

    if waqd.DEBUG_LEVEL > 0:
        Logger().info(f"DEBUG level set to {waqd.DEBUG_LEVEL}")

    from waqd.base.file_logger import SensorFileLogger
    SensorFileLogger.set_output_path(user_config_dir / "sensor_logs")
    if MIGRATE_SENSOR_LOGS:
        SensorFileLogger.migrate_txts_to_db()
        return None, None
    
    # Init components after settings, so they can use settings
    comp_ctrl()

def main():
    basic_setup()
    global comp_ctrl, settings
    if not comp_ctrl() or not settings():
        return
    # Load the selected GUI mode
    try:
        comp_ctrl().init_all()

        from waqd_station.web import start_web_server, start_web_ui_chromium_kiosk_mode

        if settings().get(STARTUP_JINGLE):
            comp_ctrl().components.sound.play(get_asset_file("sounds", "pera__introgui.wav"))

        runtime_system = RuntimeSystem()
        if runtime_system.is_target_system and not waqd_station.HEADLESS_MODE:
            Logger().info("Starting Chromium in kiosk mode...")
            chrome_browser = Thread(target=start_web_ui_chromium_kiosk_mode, daemon=True)
            chrome_browser.start()
        start_web_server(reload=waqd.DEBUG_LEVEL > 3)
        if waqd_station.HEADLESS_MODE:
            comp_ctrl().wait_for_stop()

    except Exception:
        import traceback

        trace_back = traceback.format_exc()
        Logger().error("Application crashed: \n%s", trace_back)

    # unload modules - wait for every thread to quit
    Logger().info("Prepare to exit...")
    if comp_ctrl():
        comp_ctrl().unload_all()
        while not comp_ctrl().all_unloaded:
            time.sleep(0.1)


def start_remote_debug():
    """Start remote debugging from level 2 and wait on it from level 3"""
    runtime_system = RuntimeSystem()
    if waqd.DEBUG_LEVEL > 1 and runtime_system.is_target_system:
        import debugpy  # pylint: disable=import-outside-toplevel

        port = 3003
        debugpy.listen(("0.0.0.0", port))
        if waqd.DEBUG_LEVEL > 2:
            print("Waiting to attach on port %s", port)
            debugpy.wait_for_client()  # blocks execution until client is attached



def crash_hook(exctype, excvalue, tb):
    try:
        import traceback

        tb_formatted = "\n".join(traceback.format_tb(tb, limit=10))
        error_text = f"Application crashed: {str(exctype)} {excvalue}\n{tb_formatted}"
        Logger().fatal(error_text)
    except Exception:  # just in case, otherwise we get an endless exception loop
        sys.exit(2)
    sys.exit(1)
