import json
import urllib.request
from typing import Optional
from waqd.base.network import Network
from waqd.base.file_logger import Logger
from waqd.components.weather.base_types import Location

class NominatimGeocoding:
    """
    Reverse geocoding using OpenStreetMap Nominatim API.
    Used to resolve location name from coordinates.
    """

    REVERSE_QUERY = "https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
    USER_AGENT = "WAQD-WeatherStation/1.0"

    def __init__(self):
        super().__init__()

    def reverse_geocoding(self, latitude: float, longitude: float) -> Optional[Location]:
        try:
            url = self.REVERSE_QUERY.format(lat=latitude, lon=longitude)
            request = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            
            with urllib.request.urlopen(request) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                if "error" in data:
                    Logger().warning(f"Nominatim: API error: {data['error']}")
                    return None

                address = data.get("address", {})
                
                # Determine a suitable name
                name = address.get("city") or address.get("town") or address.get("village") or address.get("suburb") or "Unknown location"
                
                return Location(
                    name=name,
                    country=address.get("country", ""),
                    country_code=address.get("country_code", ""),
                    state=address.get("state", address.get("region", "")),
                    county=address.get("county", ""),
                    latitude=latitude,
                    longitude=longitude,
                    altitude=0.0  # Nominatim doesn't provide elevation
                )
        except Exception as error:
            Logger().error(f"Nominatim: Can't resolve location for {latitude} {longitude}: {str(error)}")
            return None
