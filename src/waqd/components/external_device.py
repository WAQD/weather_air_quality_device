from waqd.base.component import Component
from typing import Dict, Any, Optional
import uuid
import asyncio
import json
from datetime import datetime

from waqd.settings import USER_API_KEY
import waqd.app as app

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    websockets = None
    WebSocketClientProtocol = None


class WAQDDeviceClient(Component):
    def __init__(self, server_url: str):
        self._server_url = server_url
        self._device_id = self.get_mac_address()
        self._user_api_key = app.settings.get_string(USER_API_KEY)
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._running = False
        
        super().__init__()
    
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
            self._logger.error("Cannot connect: No API key available")
            return
        
        if websockets is None:
            self._logger.error("websockets library not installed")
            return
        
        # Construct WebSocket URL
        ws_url = self._server_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/ws/device/{self._device_id}"
        
        headers = {
            "Authorization": f"Bearer {self._user_api_key}"
        }
        
        self._running = True
        
        try:
            async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                self._websocket = websocket
                self._logger.info(f"Connected to server: {ws_url}")
                
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
                        self._logger.error(f"Error receiving message: {e}")
                        break
        
        except Exception as e:
            self._logger.error(f"WebSocket connection error: {e}")
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
                self._logger.error(f"Error sending heartbeat: {e}")
    
    async def _handle_server_message(self, message: Dict[str, Any]):
        """Handle incoming messages from server"""
        message_type = message.get("type")
        
        if message_type == "heartbeat_ack":
            self._logger.debug("Heartbeat acknowledged")
        
        elif message_type == "command":
            command = message.get("command")
            parameters = message.get("parameters", {})
            self._logger.info(f"Received command: {command} with params: {parameters}")
            # TODO: Handle commands from server
        
        elif message_type == "pairing_request":
            username = message.get("username")
            session_id = message.get("session_id")
            self._logger.info(f"Pairing request from user: {username}")
            # TODO: Show confirmation dialog to user
        
        elif message_type == "pairing_complete":
            if message.get("success") and message.get("approved"):
                api_key = message.get("api_key")
                user_info = message.get("user_info", {})
                if api_key:
                    self.on_pairing_success(api_key, user_info)
        
        else:
            self._logger.warning(f"Unknown message type: {message_type}")
    
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
                self._logger.error(f"Error sending sensor data: {e}")
    
    def start(self):
        """Start the WebSocket client"""
        if self._user_api_key and not self._ws_task:
            self._ws_task = asyncio.create_task(self.connect_websocket())
    
    def stop(self):
        """Stop the WebSocket client"""
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
            self._ws_task = None

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
