"""
Device Connection Service for WAQD

This module handles WebSocket connections from WAQD devices and provides
REST API endpoints for device management and communication.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data models
class DeviceData(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    co2: Optional[float] = None
    pressure: Optional[float] = None
    timestamp: Optional[str] = None

class CommandData(BaseModel):
    command: str
    parameters: Optional[Dict[str, Any]] = None

class DeviceInfo(BaseModel):
    device_id: str
    connected: bool
    last_seen: Optional[str] = None
    data: Optional[DeviceData] = None

# Global device manager
class DeviceManager:
    def __init__(self):
        # device_id -> websocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # device_id -> last device data
        self.device_data: Dict[str, DeviceData] = {}
        # device_id -> last seen timestamp
        self.last_seen: Dict[str, float] = {}
        # device_id -> list of pending commands
        self.pending_commands: Dict[str, List[CommandData]] = defaultdict(list)

    def connect_device(self, device_id: str, websocket: WebSocket):
        """Register a new device connection"""
        self.active_connections[device_id] = websocket
        self.last_seen[device_id] = time.time()
        logger.info(f"Device {device_id} connected")

    def disconnect_device(self, device_id: str):
        """Remove a device connection"""
        if device_id in self.active_connections:
            del self.active_connections[device_id]
        logger.info(f"Device {device_id} disconnected")

    def update_device_data(self, device_id: str, data: DeviceData):
        """Update device data"""
        self.device_data[device_id] = data
        self.last_seen[device_id] = time.time()

    def get_device_data(self, device_id: str) -> Optional[DeviceData]:
        """Get latest device data"""
        return self.device_data.get(device_id)

    def get_connected_devices(self) -> List[str]:
        """Get list of currently connected device IDs"""
        return list(self.active_connections.keys())

    def get_all_devices(self) -> List[DeviceInfo]:
        """Get info for all known devices"""
        devices = []

        # Connected devices
        for device_id in self.active_connections.keys():
            devices.append(DeviceInfo(
                device_id=device_id,
                connected=True,
                last_seen=datetime.fromtimestamp(self.last_seen.get(device_id, 0)).isoformat(),
                data=self.device_data.get(device_id)
            ))

        # Disconnected devices (with recent data)
        for device_id, data in self.device_data.items():
            if device_id not in self.active_connections:
                devices.append(DeviceInfo(
                    device_id=device_id,
                    connected=False,
                    last_seen=datetime.fromtimestamp(self.last_seen.get(device_id, 0)).isoformat(),
                    data=data
                ))

        return devices

    def send_command_to_device(self, device_id: str, command: CommandData) -> bool:
        """Send command to device (queue if offline)"""
        if device_id in self.active_connections:
            # Device is connected, send immediately
            websocket = self.active_connections[device_id]
            try:
                message = {
                    "type": "command",
                    "command": command.command,
                    "parameters": command.parameters or {},
                    "timestamp": datetime.now().isoformat()
                }
                asyncio.create_task(websocket.send_json(message))
                logger.info(f"Sent command to {device_id}: {command.command}")
                return True
            except Exception as e:
                logger.error(f"Failed to send command to {device_id}: {e}")
                return False
        else:
            # Device is offline, queue command
            self.pending_commands[device_id].append(command)
            logger.info(f"Queued command for offline device {device_id}: {command.command}")
            return True

    def get_pending_commands(self, device_id: str) -> List[CommandData]:
        """Get pending commands for a device"""
        return self.pending_commands.get(device_id, [])

    def clear_pending_commands(self, device_id: str):
        """Clear pending commands for a device"""
        if device_id in self.pending_commands:
            del self.pending_commands[device_id]

# Global device manager instance
device_manager = DeviceManager()

async def websocket_endpoint(websocket: WebSocket, device_id: str, user_token: str = Query(...)):
    """
    WebSocket endpoint for WAQD devices to connect and communicate.

    Devices connect with: /ws/device/{device_id}?user_token=xxx
    """
    # Basic authentication check (you might want to implement proper auth)
    if not user_token or len(user_token) < 10:
        await websocket.close(code=1008, reason="Invalid user token")
        return

    await websocket.accept()
    logger.info(f"Device {device_id} attempting connection with token: {user_token[:8]}...")

    try:
        # Register device connection
        device_manager.connect_device(device_id, websocket)

        # Send any pending commands immediately
        pending_commands = device_manager.get_pending_commands(device_id)
        if pending_commands:
            for command in pending_commands:
                message = {
                    "type": "command",
                    "command": command.command,
                    "parameters": command.parameters or {},
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_json(message)
                logger.info(f"Sent pending command to {device_id}: {command.command}")

            # Clear pending commands
            device_manager.clear_pending_commands(device_id)

        # Main message loop
        while True:
            try:
                # Receive message from device
                message_str = await websocket.receive_text()
                message = json.loads(message_str)

                message_type = message.get("type")

                if message_type == "heartbeat":
                    # Respond to heartbeat
                    await websocket.send_json({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.now().isoformat()
                    })

                elif message_type == "sensor_data":
                    # Update device data
                    data_dict = message.get("data", {})
                    device_data = DeviceData(**data_dict)
                    device_manager.update_device_data(device_id, device_data)
                    logger.debug(f"Updated data for {device_id}: {data_dict}")

                elif message_type == "data_request":
                    # Server is requesting data (device-initiated)
                    current_data = device_manager.get_device_data(device_id)
                    if current_data:
                        await websocket.send_json({
                            "type": "sensor_data_response",
                            "data": current_data.dict(),
                            "timestamp": datetime.now().isoformat()
                        })

                else:
                    logger.warning(f"Unknown message type from {device_id}: {message_type}")

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {device_id}")
                continue

    except WebSocketDisconnect:
        logger.info(f"Device {device_id} disconnected")
    except Exception as e:
        logger.error(f"Error handling device {device_id}: {e}")
    finally:
        # Clean up connection
        device_manager.disconnect_device(device_id)

async def get_device_data(device_id: str):
    """
    REST API endpoint to get latest data from a device.

    GET /api/devices/{device_id}/data
    """
    data = device_manager.get_device_data(device_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found or no data available")

    return {
        "device_id": device_id,
        "data": data.dict(),
        "timestamp": datetime.now().isoformat()
    }

async def send_command_to_device(device_id: str, command: CommandData):
    """
    REST API endpoint to send a command to a device.

    POST /api/devices/{device_id}/command
    Body: {"command": "reboot", "parameters": {"delay": 5}}
    """
    success = device_manager.send_command_to_device(device_id, command)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to send command to device {device_id}")

    return {
        "success": True,
        "device_id": device_id,
        "command": command.command,
        "message": f"Command sent to device {device_id}"
    }

async def get_connected_devices():
    """
    REST API endpoint to get list of all devices (connected and known).

    GET /api/devices
    """
    devices = device_manager.get_all_devices()

    return {
        "devices": [device.dict() for device in devices],
        "total_count": len(devices),
        "connected_count": len(device_manager.get_connected_devices()),
        "timestamp": datetime.now().isoformat()
    }

# Health check endpoint (optional)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "connected_devices": len(device_manager.get_connected_devices()),
        "timestamp": datetime.now().isoformat()
    }
