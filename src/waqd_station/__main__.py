import argparse
import os
import sys
import waqd
import waqd_station

def setup_on_non_target_system():
    """Must be able to load on desktop systems"""
    mockup_path = waqd.base_path.parent.parent / "test" / "mock"
    sys.path = [str(mockup_path)] + sys.path
    os.environ["PYTHONPATH"] = str(mockup_path)  # for mh-z19
    waqd_station.user_config_dir = waqd.base_path.parent.parent / "config"
    import logging

    logging.getLogger("root").info(
        "System: Using mockups from %s", str(mockup_path)
    )  # don't use logger yet


def parse_cmd_args():
    """
    All CLI related functions.
    """

    parser = argparse.ArgumentParser(
        prog=waqd_station.PROG_NAME,
        description=f"{waqd_station.PROG_NAME} command line interface",
    )
    parser.add_argument("-v", "--version", action="version", version=waqd_station.__version__)
    parser.add_argument("-H", "--headless", action="store_true")
    parser.add_argument("-D", "--debug_level", type=int, default=waqd.DEBUG_LEVEL)
    parser.add_argument("-M", "--migrate_sensor_logs", action="store_true")

    args = parser.parse_args()
    if waqd.DEBUG_LEVEL > 0 and args.debug_level > 0:
        print("WARNING: Both cli arg and envvar are set for DEBUG_LEVEL. Prioritizing envvar.")
    if waqd.DEBUG_LEVEL == 0:
        waqd.DEBUG_LEVEL = args.debug_level
    if args.headless:
        waqd_station.HEADLESS_MODE = True
    if args.migrate_sensor_logs:
        waqd_station.MIGRATE_SENSOR_LOGS = True


def startup():
    # System is first, is_target_system is the most basic check
    from waqd.base.system import RuntimeSystem

    runtime_system = RuntimeSystem()
    if not runtime_system.is_target_system:
        setup_on_non_target_system()

    parse_cmd_args()  # cmd args set Debug level for logger
    from waqd_station.app import main

    main()


if __name__ == "__main__":
    startup()
