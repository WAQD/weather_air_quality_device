"""
Device Connection Service for WAQD

This module handles WebSocket connections from WAQD devices and provides
REST API endpoints for device management and communication.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from waqd.base.file_logger import Logger
from waqd.web.api.sensor.v1.model import SensorApi_v1_1

# Configuration
# DB_SYNC_INTERVAL: How often to sync device status to database (periodic background task)
# HEARTBEAT_DB_UPDATE_THRESHOLD: Minimum time between heartbeat-triggered DB updates
#   - Prevents DB spam from frequent heartbeats (every 30s from device)
#   - Device status is synced to DB on:
#     1. Initial connection (immediate)
#     2. Heartbeats (if >60s since last sync)
#     3. Periodic background task (every 5 minutes)
#     4. Disconnection (immediate, marks device offline)
DB_SYNC_INTERVAL = 300  # Sync to database every 5 minutes
HEARTBEAT_DB_UPDATE_THRESHOLD = 60  # Only update DB if last update was >60 seconds ago


class DeviceInfo(BaseModel):
    device_id: str
    connected: bool
    last_seen: Optional[str] = None
    data: Optional[SensorApi_v1_1] = None


class ConnectedDevice:
    """Represents a connected device with state tracking and DB sync"""

    def __init__(self, device_id: str, websocket: WebSocket):
        self.device_id = device_id
        self.websocket = websocket
        self.connected_at = time.time()
        self.last_heartbeat = time.time()
        self.last_db_sync = 0.0  # Never synced yet
        self.data: Optional[SensorApi_v1_1] = None
        self._sync_task: Optional[asyncio.Task] = None

    def update_heartbeat(self):
        """Update heartbeat timestamp"""
        self.last_heartbeat = time.time()

    def update_data(self, data: SensorApi_v1_1):
        """Update device sensor data"""
        self.data = data
        self.last_heartbeat = time.time()

    def needs_db_sync(self) -> bool:
        """Check if device state should be synced to database"""
        time_since_sync = time.time() - self.last_db_sync
        return time_since_sync >= DB_SYNC_INTERVAL

    async def sync_to_db(self, force: bool = False):
        """
        Sync device status to database

        Args:
            force: Force sync even if interval hasn't elapsed
        """
        if not force and not self.needs_db_sync():
            return

        from waqd_website.database.devices import update_device_status

        try:
            success = update_device_status(
                self.device_id, status="online", last_seen=datetime.utcnow()
            )
            if success:
                self.last_db_sync = time.time()
                Logger().debug("Synced device %s to database", self.device_id)
            else:
                Logger().warning("Failed to sync device %s to database", self.device_id)
        except Exception as e:
            Logger().error("Error syncing device %s to database: %s", self.device_id, e)

    async def disconnect(self):
        """Handle device disconnection - sync final state to DB"""
        from waqd_website.database.devices import update_device_status

        # Cancel periodic sync task if running
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()

        # Final sync to mark as offline
        try:
            update_device_status(self.device_id, status="offline", last_seen=datetime.utcnow())
            Logger().info("Device %s marked as offline in database", self.device_id)
        except Exception as e:
            Logger().error("Error marking device %s offline: %s", self.device_id, e)

    async def start_periodic_sync(self):
        """Start background task for periodic DB sync"""

        async def periodic_sync():
            while True:
                try:
                    await asyncio.sleep(DB_SYNC_INTERVAL)
                    await self.sync_to_db(force=True)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    Logger().error("Error in periodic sync for %s: %s", self.device_id, e)

        self._sync_task = asyncio.create_task(periodic_sync())

    @property
    def last_seen_datetime(self) -> datetime:
        """Get last seen as datetime"""
        return datetime.fromtimestamp(self.last_heartbeat)


# Global device manager
class DeviceManager:
    def __init__(self):
        # device_id -> ConnectedDevice instance
        self.connected_devices: Dict[str, ConnectedDevice] = {}
        # device_id -> last device data (for historical/disconnected devices)
        self.device_data: Dict[str, SensorApi_v1_1] = {}
        # device_id -> last seen timestamp (for disconnected devices)
        self.last_seen: Dict[str, float] = {}

    def connect_device(self, device_id: str, websocket: WebSocket) -> ConnectedDevice:
        """Register a new device connection"""
        device = ConnectedDevice(device_id, websocket)
        self.connected_devices[device_id] = device
        Logger().info("Device %s connected", device_id)

        # Start periodic DB sync
        asyncio.create_task(device.start_periodic_sync())

        # Initial DB sync to mark as online
        asyncio.create_task(device.sync_to_db(force=True))

        return device

    async def disconnect_device(self, device_id: str):
        """Remove a device connection and sync final state"""
        if device_id in self.connected_devices:
            device = self.connected_devices[device_id]

            # Store last known data
            if device.data:
                self.device_data[device_id] = device.data
            self.last_seen[device_id] = device.last_heartbeat

            # Sync to DB and mark offline
            await device.disconnect()

            del self.connected_devices[device_id]
        Logger().info("Device %s disconnected", device_id)

    def update_device_heartbeat(self, device_id: str):
        """Update device heartbeat timestamp"""
        if device_id in self.connected_devices:
            device = self.connected_devices[device_id]
            device.update_heartbeat()

            # Optionally sync to DB if enough time has passed
            # This avoids DB spam while keeping status reasonably fresh
            time_since_sync = time.time() - device.last_db_sync
            if time_since_sync >= HEARTBEAT_DB_UPDATE_THRESHOLD:
                asyncio.create_task(device.sync_to_db())

    def update_device_data(self, device_id: str, data: SensorApi_v1_1):
        """Update device data"""
        if device_id in self.connected_devices:
            self.connected_devices[device_id].update_data(data)
        else:
            # Store for disconnected device
            self.device_data[device_id] = data
            self.last_seen[device_id] = time.time()

    def get_device_data(self, device_id: str) -> Optional[SensorApi_v1_1]:
        """Get latest device data"""
        if device_id in self.connected_devices:
            return self.connected_devices[device_id].data
        return self.device_data.get(device_id)

    def get_connected_devices(self) -> List[str]:
        """Get list of currently connected device IDs"""
        return list(self.connected_devices.keys())

    def get_all_devices(self) -> List[DeviceInfo]:
        """Get info for all known devices"""
        devices = []

        # Connected devices
        for device_id, device in self.connected_devices.items():
            devices.append(
                DeviceInfo(
                    device_id=device_id,
                    connected=True,
                    last_seen=device.last_seen_datetime.isoformat(),
                    data=device.data,
                )
            )

        # Disconnected devices (with recent data)
        for device_id, data in self.device_data.items():
            if device_id not in self.connected_devices:
                last_seen_ts = self.last_seen.get(device_id, 0)
                devices.append(
                    DeviceInfo(
                        device_id=device_id,
                        connected=False,
                        last_seen=datetime.fromtimestamp(last_seen_ts).isoformat(),
                        data=data,
                    )
                )

        return devices

    async def send_pairing_request(
        self, device_id: str, username: str, session_id: str
    ) -> bool:
        """
        Send pairing request to device when user claims session
        Device will show confirmation dialog
        """
        if device_id not in self.connected_devices:
            Logger().warning("Cannot send pairing request - device %s not connected", device_id)
            return False

        device = self.connected_devices[device_id]
        try:
            message = {
                "type": "pairing_request",
                "username": username,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            }
            await device.websocket.send_json(message)
            Logger().info("Sent pairing request to %s for user %s", device_id, username)
            return True
        except Exception as e:
            Logger().error("Failed to send pairing request to %s: %s", device_id, e)
            return False


# User WebSocket connections for real-time device data streaming
class UserDeviceConnection:
    """Manages WebSocket connections from users watching specific devices"""

    def __init__(self):
        # device_id -> List[WebSocket] (multiple users can watch same device)
        self.user_connections: Dict[str, List[WebSocket]] = {}

    def add_user_connection(self, device_id: str, websocket: WebSocket):
        """Register a user WebSocket connection for a device"""
        if device_id not in self.user_connections:
            self.user_connections[device_id] = []
        self.user_connections[device_id].append(websocket)
        Logger().info(
            "User connected to device stream: %s (total: %d)",
            device_id,
            len(self.user_connections[device_id]),
        )

    def remove_user_connection(self, device_id: str, websocket: WebSocket):
        """Remove a user WebSocket connection"""
        if device_id in self.user_connections:
            try:
                self.user_connections[device_id].remove(websocket)
                if not self.user_connections[device_id]:
                    del self.user_connections[device_id]
                Logger().info("User disconnected from device stream: %s", device_id)
            except ValueError:
                pass

    async def broadcast_to_users(self, device_id: str, message: dict):
        """Broadcast a message to all users watching this device"""
        if device_id not in self.user_connections:
            return

        dead_connections = []
        for user_ws in self.user_connections[device_id]:
            try:
                await user_ws.send_json(message)
            except Exception as e:
                Logger().error("Error sending to user websocket: %s", e)
                dead_connections.append(user_ws)

        # Clean up dead connections
        for dead_ws in dead_connections:
            self.remove_user_connection(device_id, dead_ws)


# Global instances
device_manager = DeviceManager()
user_device_connections = UserDeviceConnection()


async def websocket_endpoint(
    websocket: WebSocket, device_id: str, authorization: str = Header(None)
):
    """
    WebSocket endpoint for WAQD devices to connect and communicate.

    Devices connect with: /ws/device/{device_id}
    Authorization header: Bearer <api_key>
    """
    from waqd_website.database.devices import verify_device_api_key

    # Validate Authorization header
    if not authorization or not authorization.startswith("Bearer "):
        await websocket.close(code=1008, reason="Invalid authorization header")
        return

    api_key = authorization[7:]  # Remove "Bearer " prefix

    # Verify API key matches device
    if not verify_device_api_key(device_id, api_key):
        Logger().warning("Invalid API key for device %s", device_id)
        await websocket.close(code=1008, reason="Invalid API key")
        return

    await websocket.accept()
    Logger().info("Device %s connected successfully", device_id)

    try:
        # Register device connection
        device_manager.connect_device(device_id, websocket)
        # Main message loop
        while True:
            try:
                # Receive message from device
                message_str = await websocket.receive_text()
                message = json.loads(message_str)

                message_type = message.get("type")

                if message_type == "heartbeat":
                    # Update heartbeat timestamp (syncs to DB if needed)
                    device_manager.update_device_heartbeat(device_id)

                    # Respond to heartbeat
                    await websocket.send_json(
                        {"type": "heartbeat_ack", "timestamp": datetime.now().isoformat()}
                    )

                elif message_type == "sensor_data":
                    # Update device data
                    data_dict = message.get("data", {})
                    device_data = SensorApi_v1_1(**data_dict)
                    device_manager.update_device_data(device_id, device_data)
                    Logger().debug("Updated data for %s: %s", device_id, data_dict)

                    # Broadcast to all connected users watching this device
                    await user_device_connections.broadcast_to_users(
                        device_id,
                        {
                            "type": "sensor_data",
                            "data": data_dict,
                            "timestamp": message.get("timestamp", datetime.now().isoformat()),
                        },
                    )

                elif message_type == "data_request":
                    # Server is requesting data (device-initiated)
                    current_data = device_manager.get_device_data(device_id)
                    if current_data:
                        await websocket.send_json(
                            {
                                "type": "sensor_data_response",
                                "data": current_data.dict(),
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                else:
                    Logger().warning("Unknown message type from %s: %s", device_id, message_type)

            except json.JSONDecodeError:
                Logger().error("Invalid JSON from %s", device_id)
                continue

    except WebSocketDisconnect:
        Logger().info("Device %s disconnected", device_id)
    except Exception as e:
        Logger().error("Error handling device %s: %s", device_id, e)
    finally:
        # Clean up connection
        await device_manager.disconnect_device(device_id)


async def get_device_data(device_id: str):
    """
    REST API endpoint to get latest data from a device.

    GET /api/devices/{device_id}/data
    """
    data = device_manager.get_device_data(device_id)
    if data is None:
        raise HTTPException(
            status_code=404, detail=f"Device {device_id} not found or no data available"
        )

    return {
        "device_id": device_id,
        "data": data.dict(),
        "timestamp": datetime.now().isoformat(),
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
        "timestamp": datetime.now().isoformat(),
    }


# Health check endpoint (optional)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "connected_devices": len(device_manager.get_connected_devices()),
        "timestamp": datetime.now().isoformat(),
    }


async def user_device_stream(websocket: WebSocket, device_id: str):
    """
    WebSocket endpoint for users to receive real-time device data

    Users connect with: /ws/user/device/{device_id}
    Requires authentication via session cookie
    """
    from waqd_website.auth.authentication import get_current_user
    from waqd_website.database.devices import get_devices_for_user

    current_user = None
    auth_failed = False

    # Authenticate user via cookie
    try:
        # Get token from cookie
        cookie_authorization = websocket.cookies.get("Authorization", "")
        if not cookie_authorization or not cookie_authorization.startswith("Bearer "):
            Logger().warning("WebSocket auth failed: no valid Authorization cookie")
            auth_failed = True
        else:
            token = cookie_authorization[7:]  # Remove "Bearer " prefix
            current_user = get_current_user(token)

            if not current_user:
                Logger().warning("WebSocket auth failed: invalid token")
                auth_failed = True
    except Exception as e:
        Logger().error("Authentication error in user_device_stream: %s", e)
        auth_failed = True

    # Accept connection first, then close if auth failed
    await websocket.accept()

    if auth_failed:
        await websocket.close(code=1008, reason="Authentication required")
        return

    # Verify user owns this device
    try:
        assert current_user
        user_devices = get_devices_for_user(current_user.username)
        device_ids = [d.device_id for d in user_devices]

        if device_id not in device_ids:
            Logger().warning(
                "User %s tried to access device %s without permission",
                current_user.username,
                device_id,
            )
            await websocket.close(code=1008, reason="Access denied")
            return
    except Exception as e:
        Logger().error("Error checking device ownership: %s", e)
        await websocket.close(code=1008, reason="Internal error")
        return

    Logger().info("User %s connected to device %s stream", current_user.username, device_id)

    try:
        # Register user connection
        user_device_connections.add_user_connection(device_id, websocket)

        # Send initial device status and latest data
        is_online = device_id in device_manager.connected_devices
        latest_data = device_manager.get_device_data(device_id)

        await websocket.send_json(
            {
                "type": "device_status",
                "status": "online" if is_online else "offline",
                "device_id": device_id,
            }
        )

        if latest_data:
            await websocket.send_json(
                {
                    "type": "sensor_data",
                    "data": latest_data.dict(),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Start periodic data request task to pull sensor data from device
        async def request_data_periodically():
            while True:
                try:
                    if device_id in device_manager.connected_devices:
                        # Send data_request command to device
                        device = device_manager.connected_devices[device_id]
                        try:
                            await device.websocket.send_json(
                                {
                                    "type": "data_request",
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                            Logger().debug("Sent data_request to device %s", device_id)
                        except Exception as e:
                            Logger().error("Error sending data_request to %s: %s", device_id, e)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    Logger().error("Error in periodic data request for %s: %s", device_id, e)
                await asyncio.sleep(10)  # Request every 10 seconds

        data_request_task = asyncio.create_task(request_data_periodically())

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message from user (e.g., ping/pong)
                message_str = await websocket.receive_text()
                message = json.loads(message_str)

                message_type = message.get("type")

                if message_type == "ping":
                    # Respond to ping
                    await websocket.send_json(
                        {"type": "pong", "timestamp": datetime.now().isoformat()}
                    )
                elif message_type == "request_data":
                    # User requests current data
                    latest_data = device_manager.get_device_data(device_id)
                    if latest_data:
                        await websocket.send_json(
                            {
                                "type": "sensor_data",
                                "data": latest_data.dict(),
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

            except json.JSONDecodeError:
                Logger().error("Invalid JSON from user websocket")
                continue

    except WebSocketDisconnect:
        Logger().info(
            "User %s disconnected from device %s stream",
            current_user.username if current_user else "unknown",
            device_id,
        )
    except Exception as e:
        Logger().error("Error in user device stream for %s: %s", device_id, e)
    finally:
        # Cancel periodic data request task
        if "data_request_task" in locals():
            data_request_task.cancel()
        user_device_connections.remove_user_connection(device_id, websocket)
