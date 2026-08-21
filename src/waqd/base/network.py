import re
import uuid
from time import sleep

from waqd.base.file_logger import Logger

try:
    import nmcli
    from nmcli import NetworkConnectivity
except ImportError:
    Logger().warning("nmcli library not found.")
from waqd.base.file_logger import Logger


class Network:
    """
    Singleton that abstracts information about the network.
    """

    _instance = None
    _disable_network = False
    _netw_counter = 0
    _inet_counter = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self._eth_device = ""
        self._wlan_device = ""

        self.refresh()
        self.is_connected_via_eth()  # init _eth_device
        self.is_connected_via_wlan()  # init _wlan_device

        self.wait_for_network()

    @staticmethod
    def get_mac_address() -> str:
        """Get MAC address of the device to use as device_id"""
        mac_num = uuid.getnode()
        mac_hex = ":".join(
            f"{(mac_num >> elements) & 0xFF:02x}" for elements in range(0, 8 * 6, 8)
        )
        return mac_hex

    def refresh(self):
        """Refresh the device and wifi network lists."""
        self._devices = nmcli.device.status()
        self._wifi_networks = nmcli.device.wifi()

    def wait_for_network(self) -> bool:
        max_error = 5
        while (
            self.get_connectivity()
            not in [NetworkConnectivity.LIMITED, NetworkConnectivity.FULL]
            and self._netw_counter < max_error
        ):
            sleep(1)
            self._netw_counter += 1
            if self._netw_counter == 0:
                Logger().info("Waiting for network...")

        self._netw_counter = 0
        if self._netw_counter == max_error:
            return False
        return True

    def wait_for_internet(self) -> bool:
        self.wait_for_network()
        max_error = 5
        while (
            not self.get_connectivity() == NetworkConnectivity.FULL
            and self._inet_counter < max_error
        ):
            sleep(1)
            self._inet_counter += 1
            if self._inet_counter == 0:
                Logger().info("Waiting for network...")

        if self._inet_counter == max_error:
            return False
        self._inet_counter = 0
        return True

    def is_connected_via_eth(self) -> bool:
        for device in self._devices:
            if device.device_type == "ethernet" and device.state == "connected":
                self._eth_device = device.device
                return True
        return False

    def is_connected_via_wlan(self) -> bool:
        for device in self._devices:
            if device.device_type == "wifi" and device.state == "connected":
                self._wlan_device = device.device
                return True
        return False

    def list_wifi(self, include_hidden=False):
        # filter out duplicates
        self._wifi_networks = nmcli.device.wifi()
        wifi_networks = {}
        for device in self._wifi_networks:
            if not device.ssid:
                if not include_hidden:
                    continue
            same_device = wifi_networks.get(device.ssid, "")
            if same_device and same_device.in_use:
                continue
            wifi_networks[device.ssid] = device
        return wifi_networks

    def current_wifi_strength(self) -> int | None:
        for device in self._wifi_networks:
            if device.in_use:
                return device.signal
        return None

    def connect_wifi(self, ssid: str, password: str):
        Logger().info("Network: Connecting to WiFi: %s", ssid)
        nmcli.device.wifi_connect(ssid, password)

    def try_connect_wifi(self, ssid: str):
        cmd = ["device", "wifi", "connect", ssid]
        r = nmcli._syscmd.nmcli(cmd)
        m = re.search(r"Connection activation failed:", r)
        if m:
            raise nmcli.ConnectionActivateFailedException("Connection activation failed")

    def disconnect_wifi(self):
        Logger().info("Network: Disconnecting from WiFi")
        if self.is_connected_via_wlan():
            nmcli.device.disconnect(self._wlan_device)

    def enable_wifi(self):
        Logger().info("Network: Enabling WiFi")
        nmcli.radio.wifi_on()

    def disable_wifi(self):
        Logger().info("Network: Disabling WiFi")
        nmcli.radio.wifi_off()

    def wifi_enabled(self):
        return nmcli.radio.wifi()

    def get_connectivity(self) -> NetworkConnectivity:
        return nmcli.networking.connectivity(check=True)

    def is_fully_connected(self) -> bool:
        """Return True, if the device has full internet connectivity."""
        return self.get_connectivity() == NetworkConnectivity.FULL

    def restart_wlan(self):
        self.disable_wifi()
        sleep(2)
        self.enable_wifi()  # reconnects
