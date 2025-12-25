import os
from waqd.base.component import Component
from typing import Dict, Any, Optional
import uuid
import asyncio
import json
from datetime import datetime
import threading

from waqd.settings import USER_API_KEY
import waqd.app as app


import websockets

from waqd.web.api.sensor.v1.connector import SensorRetrieval

class WAQDDeviceClient(Component):
    def __init__(self):
        self._server_url = os.getenv("WAQD_WEBSITE_ADDRESS", "https://waqd.de")
        self._device_id = self.get_mac_address()
        self._user_api_key = app.settings.get_string(USER_API_KEY)
        self._websocket: Optional[Any] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        
        super().__init__()

        self.start()
    
    @staticmethod
    def get_mac_address() -> str:
        """Get MAC address of the device to use as device_id"""
        mac_num = uuid.getnode()
        mac_hex = ':'.join(f'{(mac_num >> elements) & 0xff:02x}' 
                          for elements in range(0, 8*6, 8))
        return mac_hex

    async def connect_websocket(self):
        """
        Establish WebSocket connection to the server
        """
        if not self._user_api_key:
            self._logger.error("WS: Cannot connect: No API key available")
            return

        # Construct WebSocket URL
        ws_url = self._server_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/ws/device/{self._device_id}"
        
        headers = {
            "Authorization": f"Bearer {self._user_api_key}"
        }
        
        self._running = True
        
        try:
            async with websockets.connect(ws_url, additional_headers=headers) as websocket:
                self._websocket = websocket
                self._logger.info("WS: Connected to server: %s", ws_url)
                
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
                    except Exception as e:
                        self._logger.error("WS: Error receiving message: %s", e)
                        break
        
        except Exception as e:
            self._logger.error("WS: WebSocket connection error: %s", e)
        finally:
            self._websocket = None
            if self._running:
                # Reconnect after 5 seconds if still running
                await asyncio.sleep(5)
                if self._running:
                    await self.connect_websocket()
    
    async def _send_heartbeat(self):
        """Send heartbeat to server"""
        if self._websocket:
            try:
                await self._websocket.send(json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }))
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
                await self._websocket.send(json.dumps({
                    "type": "sensor_data",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }))
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
