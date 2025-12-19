from waqd.base.component import CyclicComponent
import requests
import time
import threading
from datetime import datetime
from typing import Dict, Any

import asyncio
import websockets
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any


class WAQDDeviceClient:
    def __init__(self, server_url: str, device_id: str, user_token: str):
        self.server_url = server_url
        self.device_id = device_id
        self.user_token = user_token
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.running = False
        self.reconnect_delay = 5  # seconds

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    async def connect(self):
        """Connect to the server WebSocket"""
        uri = f"{self.server_url}/ws/device/{self.device_id}?user_token={self.user_token}"
        try:
            self.websocket = await websockets.connect(uri)
            self.logger.info("Connected to server: %s", uri)
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False

    async def disconnect(self):
        """Disconnect from server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    async def send_message(self, message: Dict[str, Any]):
        """Send message to server"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(message))
                self.logger.debug("Sent message: %s", message)
            except Exception as e:
                self.logger.error(f"Failed to send message: {e}")

    async def handle_server_message(self, message: Dict[str, Any]):
        """Handle incoming messages from server"""
        msg_type = message.get("type")

        if msg_type == "heartbeat_ack":
            self.logger.debug("Received heartbeat ack")

        elif msg_type == "data_request":
            # Server is requesting current sensor data
            sensor_data = self.get_current_sensor_data()
            await self.send_message(
                {
                    "type": "sensor_data",
                    "data": sensor_data,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        elif msg_type == "command":
            # Server sent a command (e.g., from web interface)
            command = message.get("command", {})
            self.logger.info("Received command: %s", command)
            # Handle command here (e.g., change settings, trigger actions)

    def get_current_sensor_data(self) -> Dict[str, Any]:
        """Get current sensor readings (mock data for testing)"""
        return {
            "temperature": 22.5,
            "humidity": 45.2,
            "co2": 420,
            "pressure": 1013.25,
            "timestamp": datetime.now().isoformat(),
        }

    async def send_heartbeat(self):
        """Send periodic heartbeat to server"""
        await self.send_message({"type": "heartbeat", "timestamp": datetime.now().isoformat()})

    async def send_sensor_data(self):
        """Send sensor data to server"""
        data = self.get_current_sensor_data()
        await self.send_message(
            {"type": "sensor_data", "data": data, "timestamp": datetime.now().isoformat()}
        )

    async def message_handler(self):
        """Handle incoming messages from server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_server_message(data)
                except json.JSONDecodeError as e:
                    self.logger.error("Failed to decode message: %s", e)
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("Connection closed by server")
        except Exception as e:
            self.logger.error("Message handler error: %s", e)

    async def periodic_tasks(self):
        """Run periodic tasks (heartbeat, sensor data) with dynamic heartbeat interval"""
        base_heartbeat_interval = 30  # seconds
        data_interval = 60  # seconds
        max_heartbeat_interval = 300  # 5 minutes when inactive

        last_heartbeat = 0
        last_data_send = 0
        last_activity = time.time()  # Track last data send for dynamic heartbeat

        while self.running:
            current_time = time.time()

            # Dynamic heartbeat: slower if no recent data activity
            time_since_activity = current_time - last_activity
            heartbeat_interval = min(
                base_heartbeat_interval + (time_since_activity / 60) * 10, max_heartbeat_interval
            )  # Increase by 10s per minute inactive

            # Send heartbeat if interval passed
            if current_time - last_heartbeat >= heartbeat_interval:
                if await self.connect():
                    try:
                        await self.send_heartbeat()
                        last_heartbeat = current_time
                    finally:
                        await self.disconnect()

            # Send sensor data if interval passed
            if current_time - last_data_send >= data_interval:
                if await self.connect():
                    try:
                        await self.send_sensor_data()
                        last_data_send = current_time
                        last_activity = current_time  # Reset activity timer
                    finally:
                        await self.disconnect()

            await asyncio.sleep(1)

    async def run_with_reconnect(self):
        """Main loop - no continuous connection, connections handled in periodic_tasks"""
        await self.periodic_tasks()

    async def start(self):
        """Start the device client"""
        self.running = True
        self.logger.info("Starting WAQD device client %s", self.device_id)
        await self.run_with_reconnect()

    def stop(self):
        """Stop the device client"""
        self.running = False
