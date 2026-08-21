from time import sleep

from waqd.base.component import CyclicComponent
from waqd.base.network import Network
from waqd.base.system import RuntimeSystem
from waqd.settings.settings import Settings
from waqd_station.settings import (
    NETWORK_RESTART_SYSTEM_ENABLED,
    NETWORK_RESTART_WLAN_ENABLED,
)


class NetworkManager(CyclicComponent):
    """
    Monitors the internet connection and applies recovery strategies.
    The WLAN adapter is restarted after the second consecutive failure.
    If that doesn't help, the RPi reboots on the next failure.
    Both recovery strategies can be toggled via the builtin settings.
    """

    UPDATE_TIME = 5  # in seconds
    INIT_WAIT_TIME = 0
    STOP_TIMEOUT = 5

    def __init__(self, components, settings: Settings):
        super().__init__(components, settings=settings)
        self._network = Network()
        self._runtime_system = RuntimeSystem()
        self._internet_reconnect_try = 0
        self._internet_connected_once = False
        self._restart_wlan_enabled = settings.get_bool(NETWORK_RESTART_WLAN_ENABLED)
        self._restart_system_enabled = settings.get_bool(NETWORK_RESTART_SYSTEM_ENABLED)
        self._start_update_loop(None, self._ensure_internet_connection)

    def _ensure_internet_connection(self):
        """Check the connection and apply the configured recovery strategy."""
        self._network.refresh()
        if self._internet_connected_once:  # at least once connected:
            if self._internet_reconnect_try == 2 and self._restart_wlan_enabled:
                if (
                    not self._network.is_connected_via_eth()
                    and self._network.is_connected_via_wlan()
                ):
                    self._logger.error("Network: Restarting wlan - Net failure...")
                    self._network.restart_wlan()
                sleep(5)
            # failed 3 times straight - restart linux
            if self._internet_reconnect_try == 3 and self._restart_system_enabled:
                # TODO dialog!
                self._logger.error("Network: Restarting system - Net failure...")
                self._runtime_system.restart()
        if not self._network.is_fully_connected():
            self._internet_reconnect_try += 1
            sleep(5)
        else:
            self._internet_connected_once = True
            if self._internet_reconnect_try != 0:
                self._internet_reconnect_try = 0
                # TODO emit signal
