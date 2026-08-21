import asyncio
import json
import os
import threading
from dataclasses import asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

import websockets

import waqd_station.app as app
from waqd.base.component import Component
from waqd_station.settings import USER_API_KEY
from waqd_station.ui.api.sensor.v1.connector import SensorRetrieval
from waqd_station.ui.api.weather.v1.connector import WeatherRetrieval

if TYPE_CHECKING:
    from waqd_station.app.component_reg import ComponentRegistry

class WAQDDeviceClient(Component):
    def __init__(self, components: "ComponentRegistry", user_api_key: str, device_id: str):
        super().__init__(components)
        self._comps: "ComponentRegistry"
        self._reload_forbidden = True

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
        self._device_owners = []  # List of users who own this device (from server)

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
            # Also send weather data
            await self._send_current_weather_data()
        elif message_type == "sensor_history_request":
            # Server requesting sensor history with specific time range and sensor type
            hours = int(message.get("hours", 12))
            sensor_type = message.get("sensor_type")
            self._logger.info(
                "WS: Received sensor_history_request for %s (%d hours)",
                sensor_type or "all sensors",
                hours
            )
            await self._send_sensor_history_data(hours=hours, sensor_type=sensor_type)
        elif message_type == "device_owners":
            # Server sending list of users who own this device
            owners = message.get("owners", [])
            self._device_owners = owners
            self._logger.info("WS: Device owners updated: %s", owners)
        else:
            self._logger.warning("WS: Unknown message type: %s", message_type)

    async def _send_current_sensor_data(self):
        """Collect and send current sensor data"""
        try:
            data = SensorRetrieval().get_interior_sensor_values()
            await self.send_sensor_data(data.model_dump())
        except Exception as e:
            self._logger.error("WS: Error collecting/sending sensor data: %s", e)

    async def _send_sensor_history_data(
        self, hours: int = 12, sensor_type: Optional[str] = None
    ):
        """Collect and send sensor history data for interior sensors
        
        Args:
            hours: Number of hours of history to send
            sensor_type: Specific sensor type to send (e.g., 'temp_degC'), or None for all
        """
        try:
            from waqd.components.sensor_base import SensorValueLogger
            
            # Define all available sensors
            all_sensors = [
                {'location': 'interior', 'type': 'temp_degC', 'hours': hours},
                {'location': 'interior', 'type': 'humidity_%', 'hours': hours},
                {'location': 'interior', 'type': 'CO2_ppm', 'hours': hours},
                {'location': 'interior', 'type': 'pressure_hPa', 'hours': hours},
            ]
            
            # Filter to only requested sensor type if specified
            if sensor_type:
                sensors = [s for s in all_sensors if s['type'] == sensor_type]
                if not sensors:
                    self._logger.warning("WS: Unknown sensor type requested: %s", sensor_type)
                    return
            else:
                sensors = all_sensors
            
            history_data = {}
            
            # Helper function for threaded execution
            def fetch_history(sensor):
                try:
                    return sensor['type'], SensorValueLogger.get_sensor_values(
                        sensor['location'],
                        sensor['type'],
                        minutes_to_read=sensor['hours'] * 60
                    )
                except Exception as e:
                    self._logger.warning("WS: Failed to get history for %s: %s", sensor['type'], e)
                    return sensor['type'], []

            # Use thread pool to avoid blocking async loop with synchronous DB/File IO
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=len(sensors)) as executor:
                results = list(executor.map(fetch_history, sensors))

            for sensor_type_name, time_value_pairs in results:
                if not time_value_pairs:
                    continue
                
                # Convert to serializable format
                data_points = [
                    {
                        'timestamp': dt.isoformat(),
                        'value': float(value)
                    }
                    for dt, value in time_value_pairs
                ]
                
                history_data[sensor_type_name] = data_points
            
            if history_data:
                await self.send_sensor_history_data(history_data)
        except Exception as e:
            self._logger.error("WS: Error collecting/sending sensor history: %s", e)

    async def _send_current_weather_data(self):
        """Collect and send current weather data"""
        try:
            weather_retrieval = WeatherRetrieval()
            current_weather = weather_retrieval.get_current_weather()
            if current_weather:
                # Convert dataclass to dict
                weather_dict = asdict(current_weather)
                # Convert datetime and time objects to ISO strings
                weather_dict['date_time'] = current_weather.date_time.isoformat()
                weather_dict['fetch_time'] = current_weather.fetch_time.isoformat()
                weather_dict['sunrise'] = current_weather.sunrise.isoformat()
                weather_dict['sunset'] = current_weather.sunset.isoformat()
                await self.send_weather_data(weather_dict)
            
            # Also send forecast data
            await self._send_forecast_data()
            # Also send hourly forecast data
            await self._send_hourly_forecast_data()
        except Exception as e:
            self._logger.error("WS: Error collecting/sending weather data: %s", e)

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

    async def send_sensor_history_data(self, data: Dict[str, Any]):
        """Send sensor history data to server"""
        if self._websocket:
            try:
                await self._websocket.send(
                    json.dumps(
                        {
                            "type": "sensor_history_data",
                            "data": data,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )
                self._logger.debug("WS: Sensor history data sent successfully")
            except Exception as e:
                self._logger.error("Error sending sensor history data: %s", e)

    async def _send_forecast_data(self):
        """Collect and send forecast weather data"""
        try:
            weather_retrieval = WeatherRetrieval()
            forecast = weather_retrieval.get_7_day_forecast()
            if forecast:
                # Convert list of dataclasses to list of dicts
                forecast_list = []
                for day in forecast:
                    day_dict = asdict(day)
                    # Convert datetime and time objects to ISO strings
                    day_dict['date_time'] = day.date_time.isoformat()
                    day_dict['fetch_time'] = day.fetch_time.isoformat()
                    day_dict['sunrise'] = day.sunrise.isoformat()
                    day_dict['sunset'] = day.sunset.isoformat()
                    forecast_list.append(day_dict)
                await self.send_forecast_data(forecast_list)
        except Exception as e:
            self._logger.error("WS: Error collecting/sending forecast data: %s", e)

    async def send_weather_data(self, data: Dict[str, Any]):
        """Send weather data to server"""
        if self._websocket:
            try:
                await self._websocket.send(
                    json.dumps(
                        {
                            "type": "weather_data",
                            "data": data,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )
                self._logger.debug("WS: Weather data sent successfully")
            except Exception as e:
                self._logger.error("Error sending weather data: %s", e)

    async def _send_hourly_forecast_data(self):
        """Collect and send hourly forecast weather data"""
        try:
            weather_provider = self._comps.weather_info
            if not weather_provider:
                return

            forecast = weather_provider.get_7_day_forecast()
            if not forecast:
                return

            # Convert hourly data to serializable format
            daytime_data = []
            nighttime_data = []

            for day_idx in range(len(forecast)):
                day_points = weather_provider.get_hourly_forecast(day_idx)
                day_daytime = []
                day_nighttime = []

                for point in day_points:
                    point_dict = asdict(point)
                    # Convert datetime and time objects to ISO strings
                    point_dict['date_time'] = point.date_time.isoformat()
                    point_dict['fetch_time'] = point.fetch_time.isoformat()
                    point_dict['sunrise'] = point.sunrise.isoformat()
                    point_dict['sunset'] = point.sunset.isoformat()

                    if point.is_daytime():
                        day_daytime.append(point_dict)
                    else:
                        day_nighttime.append(point_dict)

                daytime_data.append(day_daytime)
                nighttime_data.append(day_nighttime)
            
            await self.send_hourly_forecast_data(daytime_data, nighttime_data)
        except Exception as e:
            self._logger.error("WS: Error collecting/sending hourly forecast data: %s", e)

    async def send_forecast_data(self, data: list[Dict[str, Any]]):
        """Send forecast data to server"""
        if self._websocket:
            try:
                await self._websocket.send(
                    json.dumps(
                        {
                            "type": "forecast_data",
                            "data": data,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )
                self._logger.debug("WS: Forecast data sent successfully")
            except Exception as e:
                self._logger.error("Error sending forecast data: %s", e)

    async def send_hourly_forecast_data(
        self,
        daytime_data: list[list[Dict[str, Any]]],
        nighttime_data: list[list[Dict[str, Any]]],
    ):
        """Send hourly forecast data to server"""
        if self._websocket:
            try:
                await self._websocket.send(
                    json.dumps(
                        {
                            "type": "hourly_forecast_data",
                            "daytime": daytime_data,
                            "nighttime": nighttime_data,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )
                self._logger.debug("WS: Hourly forecast data sent successfully")
            except Exception as e:
                self._logger.error("Error sending hourly forecast data: %s", e)

    def _run_event_loop(self):
        """Run the event loop in a separate thread"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self.connect_websocket())
        except Exception as e:
            self._logger.error("WS: Event loop error: %s", e)
        finally:
            self._logger.info("WS: Event loop stopped")
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

    def get_device_owners(self) -> list[Dict[str, Any]]:
        """Get list of users who own this device (from WebSocket server)"""
        return self._device_owners.copy() if self._device_owners else []

    def on_pairing_success(self, api_key: str, user_info: Dict[str, Any]):
        """
        Called when pairing is successfully completed
        user_info contains: username, user_id, etc.
        """
        self._logger.info("Device paired with user: %s", user_info.get("username"))

        # Store the API key
        self._user_api_key = api_key
        app.settings().set(USER_API_KEY, self._user_api_key)

        # Restart WebSocket connection with new API key
        self.stop()
        self.start()
