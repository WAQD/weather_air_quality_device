import os
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel, create_engine

password = os.getenv("DATABASE_PW", "waqd_root_pw")
if POSTGRES_URL := os.getenv("POSTGRES_URL"):
    DATABASE_URL = f"postgresql+psycopg2://postgres:{password}@{POSTGRES_URL}/waqd_userdata"
elif MARIADB_URL := os.getenv("MARIADB_URL"):
    DATABASE_URL = f"mariadb+pymysql://root:{password}@{MARIADB_URL}/waqd_userdata"
else:
    DATABASE_URL = "sqlite:///./waqd_userdata.db"  # SQLite for development

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


class UserDeviceLink(SQLModel, table=True):
    """Many-to-many relationship table between users and devices"""

    __tablename__ = "user_device_link"  # type: ignore

    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)
    device_id: Optional[int] = Field(default=None, foreign_key="device.id", primary_key=True)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=255)
    email: Optional[str] = Field(default=None, index=True, unique=True, max_length=255)
    hashed_password: str = Field(default=None, max_length=255)
    disabled: Optional[bool] = False
    permissions: List[str] = Field(default_factory=list, sa_column=Column(JSON, default=[]))

    # Relationships
    devices: List["Device"] = Relationship(back_populates="owners", link_model=UserDeviceLink)


class Device(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Unique identifier like WAQD-001
    device_id: str = Field(index=True, unique=True, max_length=255)
    name: Optional[str] = Field(default=None, max_length=255)
    location: Optional[str] = Field(default=None, max_length=500)
    status: str = Field(default="offline", max_length=50)  # online, offline
    last_seen: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Long-lived API key for device authentication (128 character hex string)
    api_key: Optional[str] = Field(default=None, max_length=256, index=True)

    # Relationships
    owners: List[User] = Relationship(back_populates="devices", link_model=UserDeviceLink)


class RegistrationStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DeviceRegistrationSession(SQLModel, table=True):
    """Temporary sessions for device-to-account pairing"""

    __tablename__ = "device_registration_session"  # type: ignore

    session_id: str = Field(primary_key=True, max_length=36)
    device_id: str = Field(index=True, max_length=255)
    passphrase: str = Field(index=True, max_length=6)
    status: str = Field(default=RegistrationStatus.PENDING, max_length=20)
    expires_at: datetime
    requesting_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    claimed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    location: str = Field(default=None, max_length=255)


class ServerConfig(SQLModel, table=True):
    """Server configuration key-value store"""

    __tablename__ = "server_config"  # type: ignore

    key: str = Field(primary_key=True, max_length=255)
    value: str = Field(max_length=1024)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserWeatherLocation(SQLModel, table=True):
    """Persisted per-user weather location for website weather lookups."""

    __tablename__ = "user_weather_location"  # type: ignore

    user_id: int = Field(primary_key=True, foreign_key="user.id")
    name: str = Field(default="", max_length=255)
    country: str = Field(default="", max_length=255)
    state: str = Field(default="", max_length=255)
    county: str = Field(default="", max_length=255)
    country_code: str = Field(default="", max_length=16)
    altitude: float = Field(default=0.0)
    latitude: float = Field(default=0.0)
    longitude: float = Field(default=0.0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PasswordResetToken(SQLModel, table=True):
    """Short-lived, single-use tokens for password reset via email"""

    __tablename__ = "password_reset_token"  # type: ignore

    token_hash: str = Field(primary_key=True, max_length=64)  # SHA-256 hex digest
    user_id: int = Field(foreign_key="user.id")
    expires_at: datetime
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Create database tables - must be last

def create_db_tables():
    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Failed to create database tables: %s", e)
        raise
