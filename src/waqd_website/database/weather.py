from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from waqd.components.weather.base_types import Location
from waqd_website.database import UserWeatherLocation, engine


def get_user_weather_location(user_id: int) -> Optional[Location]:
    with Session(engine) as session:
        statement = select(UserWeatherLocation).where(UserWeatherLocation.user_id == user_id)
        saved_location = session.exec(statement).first()
        if saved_location is None:
            return None
        return Location(
            name=saved_location.name,
            country=saved_location.country,
            state=saved_location.state,
            county=saved_location.county,
            country_code=saved_location.country_code,
            altitude=saved_location.altitude,
            latitude=saved_location.latitude,
            longitude=saved_location.longitude,
        )


def save_user_weather_location(user_id: int, location: Location) -> Location:
    with Session(engine) as session:
        statement = select(UserWeatherLocation).where(UserWeatherLocation.user_id == user_id)
        saved_location = session.exec(statement).first()

        if saved_location is None:
            saved_location = UserWeatherLocation(user_id=user_id)

        saved_location.name = location.name
        saved_location.country = location.country
        saved_location.state = location.state
        saved_location.county = location.county
        saved_location.country_code = location.country_code
        saved_location.altitude = location.altitude
        saved_location.latitude = location.latitude
        saved_location.longitude = location.longitude
        saved_location.updated_at = datetime.utcnow()

        session.add(saved_location)
        session.commit()

    return location


def clear_user_weather_location(user_id: int) -> bool:
    with Session(engine) as session:
        statement = select(UserWeatherLocation).where(UserWeatherLocation.user_id == user_id)
        saved_location = session.exec(statement).first()
        if saved_location is None:
            return False
        session.delete(saved_location)
        session.commit()
        return True
