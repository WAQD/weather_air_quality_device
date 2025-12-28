import asyncio
import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional

import websockets

import waqd.app as app
from waqd.base.component import Component
from waqd.settings import USER_API_KEY
from waqd.web.api.sensor.v1.connector import SensorRetrieval


class WAQDDeviceClient(Component):
    def __init__(self, user_api_key: str, device_id:str):
        super().__init__()

        self._device_id = device_id
        self._user_api_key = user_api_key
        self._server_url = os.getenv("WAQD_WEBSITE_ADDRESS", "https://waqd.de")

        self._websocket: Optional[Any] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._reconnect_delay = 5  # Initial reconnect delay in seconds
        self._max_reconnect_delay = 300  # Max 5 minutes
        self._reconnect_attempts = 0

        self.start()

    async def connect_websocket(self):
        """
        Establish WebSocket connection to the server with exponential backoff
        """
        if not self._user_api_key:
            self._logger.error("WS: Cannot connect: No API key available")
            return

        # Construct WebSocket URL
        ws_url = self._server_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/ws/device/{self._device_id}"

        headers = {"Authorization": f"Bearer {self._user_api_key}"}

        while self._running:
            try:
                # Calculate reconnection delay with exponential backoff
                if self._reconnect_attempts > 0:
                    delay = min(
                        self._reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
                        self._max_reconnect_delay,
                    )
                    self._logger.info(
                        "WS: Reconnecting in %d seconds (attempt %d)...",
                        delay,
                        self._reconnect_attempts + 1,
                    )
                    await asyncio.sleep(delay)

                self._logger.info("WS: Attempting to connect to %s", ws_url)

                async with websockets.connect(
                    ws_url,
                    additional_headers=headers,
                    ping_interval=20,  # Send ping every 20 seconds
                    ping_timeout=10,  # Wait 10 seconds for pong
                    close_timeout=10,  # Timeout for close handshake
                ) as websocket:
                    self._websocket = websocket
                    self._reconnect_attempts = 0  # Reset on successful connection
                    self._logger.info("WS: Successfully connected to server")

                    # Send initial heartbeat
                    await self._send_heartbeat()

                    # Start message loop
                    while self._running:
                        try:
                            message_str = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                            message = json.loads(message_str)
                            await self._handle_server_message(message)
                        except asyncio.TimeoutError:
                            # Send heartbeat every 30 seconds
                            await self._send_heartbeat()
                        except websockets.exceptions.ConnectionClosed:
                            self._logger.warning("WS: Connection closed by server")
                            break
                        except json.JSONDecodeError as e:
                            self._logger.error("WS: Invalid JSON received: %s", e)
                        except Exception as e:
                            self._logger.error("WS: Error receiving message: %s", e)
                            break

            except websockets.exceptions.InvalidStatus as e:
                self._logger.error(
                    "WS: Invalid status code %s - check authentication", e.response.status_code
                )
                self._reconnect_attempts += 1
            except websockets.exceptions.WebSocketException as e:
                self._logger.error("WS: WebSocket error: %s", e)
                self._reconnect_attempts += 1
            except OSError as e:
                self._logger.error("WS: Network error: %s", e)
                self._reconnect_attempts += 1
            except Exception as e:
                self._logger.error("WS: Unexpected connection error: %s", e)
                self._reconnect_attempts += 1
            finally:
                self._websocket = None

            # If we're not running anymore, exit the loop
            if not self._running:
                break

    async def _send_heartbeat(self):
        """Send heartbeat to server"""
        if self._websocket:
            try:
                await self._websocket.send(
                    json.dumps({"type": "heartbeat", "timestamp": datetime.now().isoformat()})
                )
            except Exception as e:
                self._logger.error("WS: Error sending heartbeat: %s", e)

    async def _handle_server_message(self, message: Dict[str, Any]):
        """Handle incoming messages from server"""
        message_type = message.get("type")

        if message_type == "heartbeat_ack":
            self._logger.debug("WS: Heartbeat acknowledged")
        elif message_type == "data_request":
            # Server requesting immediate sensor data
            await self._send_current_sensor_data()

        else:
            self._logger.warning("WS: Unknown message type: %s", message_type)

    async def _send_current_sensor_data(self):
        """Collect and send current sensor data"""
        try:
            data = SensorRetrieval().get_interior_sensor_values()
            await self.send_sensor_data(data.model_dump())
        except Exception as e:
            self._logger.error("WS: Error collecting/sending sensor data: %s", e)

    async def send_sensor_data(self, data: Dict[str, Any]):
        """Send sensor data to server"""
        if self._websocket:
            try:
                await self._websocket.send(
                    json.dumps(
                        {
                            "type": "sensor_data",
                            "data": data,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )
            except Exception as e:
                self._logger.error("Error sending sensor data: %s", e)

    def _run_event_loop(self):
        """Run the event loop in a separate thread"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self.connect_websocket())
        except Exception as e:
            self._logger.error("Event loop error: %s", e)
        finally:
            self._loop.close()
            self._loop = None

    def start(self):
        """Start the WebSocket client"""
        if self._user_api_key and not self._ws_thread:
            self._running = True
            self._ws_thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self._ws_thread.start()

    def stop(self):
        """Stop the WebSocket client"""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._ws_thread:
            self._ws_thread.join(timeout=5)
            self._ws_thread = None

    def on_pairing_success(self, api_key: str, user_info: Dict[str, Any]):
        """
        Called when pairing is successfully completed
        user_info contains: username, user_id, etc.
        """
        self._logger.info("Device paired with user: %s", user_info.get("username"))

        # Store the API key
        self._user_api_key = api_key
        app.settings.set(USER_API_KEY, self._user_api_key)

        # Restart WebSocket connection with new API key
        self.stop()
        self.start()
