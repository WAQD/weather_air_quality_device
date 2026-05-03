from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from waqd.components.weather.base_types import Location
from waqd_website.database import UserWeatherLocation, UserSavedWeatherLocation, engine


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


def get_user_saved_locations(user_id: int) -> list[Location]:
    with Session(engine) as session:
        statement = select(UserSavedWeatherLocation).where(UserSavedWeatherLocation.user_id == user_id)
        saved_locations = session.exec(statement).all()
        
        return [
            Location(
                name=loc.name,
                country=loc.country,
                state=loc.state,
                county=loc.county,
                country_code=loc.country_code,
                altitude=loc.altitude,
                latitude=loc.latitude,
                longitude=loc.longitude,
            )
            for loc in saved_locations
        ]


def add_user_saved_location(user_id: int, location: Location) -> None:
    with Session(engine) as session:
        # Check if already exists based on lat/lon (approximate)
        statement = select(UserSavedWeatherLocation).where(
            UserSavedWeatherLocation.user_id == user_id
        )
        existing = session.exec(statement).all()
        for loc in existing:
            if abs(loc.latitude - location.latitude) < 0.001 and abs(loc.longitude - location.longitude) < 0.001:
                return  # already saved

        new_loc = UserSavedWeatherLocation(
            user_id=user_id,
            name=location.name,
            country=location.country,
            state=location.state,
            county=location.county,
            country_code=location.country_code,
            altitude=location.altitude,
            latitude=location.latitude,
            longitude=location.longitude,
        )
        session.add(new_loc)
        session.commit()


def delete_user_saved_location(user_id: int, latitude: float, longitude: float) -> bool:
    with Session(engine) as session:
        statement = select(UserSavedWeatherLocation).where(UserSavedWeatherLocation.user_id == user_id)
        all_locs = session.exec(statement).all()
        
        deleted_any = False
        for loc in all_locs:
            if abs(loc.latitude - latitude) < 0.001 and abs(loc.longitude - longitude) < 0.001:
                session.delete(loc)
                deleted_any = True
                
        if deleted_any:
            session.commit()
            
        return deleted_any
