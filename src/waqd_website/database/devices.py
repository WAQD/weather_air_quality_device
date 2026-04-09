from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from waqd.base.file_logger import Logger
from waqd_website.database import (
    Device,
    User,
    UserDeviceLink,
    engine,
)

# Device management functions


def get_devices_for_user(username: str) -> List[Device]:
    """Get all devices owned by a user"""
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()

        if not user:
            return []

        # Get devices through the relationship
        statement = select(Device).join(UserDeviceLink).where(UserDeviceLink.user_id == user.id)
        devices = session.exec(statement).all()
        return list(devices)


def get_device_by_id(device_id: str) -> Optional[Device]:
    """Get a device by its device_id"""
    with Session(engine) as session:
        statement = select(Device).where(Device.device_id == device_id)
        device = session.exec(statement).first()
        return device


def get_device_owners(device_id: str) -> List[User]:
    """Get all users who own a specific device"""
    with Session(engine) as session:
        device = session.exec(select(Device).where(Device.device_id == device_id)).first()
        if not device:
            return []
        
        # Get users through the relationship
        statement = select(User).join(UserDeviceLink).where(UserDeviceLink.device_id == device.id)
        users = session.exec(statement).all()
        return list(users)


def delete_device(device_id: str, username: str) -> bool:
    """Delete a device if the user is an owner"""
    with Session(engine) as session:
        # Get the device
        device = session.exec(select(Device).where(Device.device_id == device_id)).first()

        if not device:
            return False

        # Get the user
        user = session.exec(select(User).where(User.username == username)).first()

        if not user:
            return False

        # Check if user is an owner
        link = session.exec(
            select(UserDeviceLink).where(
                UserDeviceLink.user_id == user.id, UserDeviceLink.device_id == device.id
            )
        ).first()

        if not link:
            return False  # User is not an owner

        # Delete the device (cascades to links)
        session.delete(device)
        session.commit()
        return True


def update_device(
    device_id: str,
    username: str,
    name: Optional[str] = None,
    location: Optional[str] = None,
) -> Optional[Device]:
    """Update a device's information if the user is an owner"""
    with Session(engine) as session:
        # Get the device
        device = session.exec(select(Device).where(Device.device_id == device_id)).first()

        if not device:
            return None

        # Get the user
        user = session.exec(select(User).where(User.username == username)).first()

        if not user:
            return None

        # Check if user is an owner
        link = session.exec(
            select(UserDeviceLink).where(
                UserDeviceLink.user_id == user.id, UserDeviceLink.device_id == device.id
            )
        ).first()

        if not link:
            return None  # User is not an owner

        # Update device
        if name is not None:
            device.name = name
        if location is not None:
            device.location = location

        session.add(device)
        session.commit()
        session.refresh(device)
        return device


def add_device_owner(
    device_id: str, new_owner_username: str, current_owner_username: str
) -> bool:
    """Add another owner to a device (must be called by an existing owner)"""
    with Session(engine) as session:
        # Get the device
        device = session.exec(select(Device).where(Device.device_id == device_id)).first()

        if not device:
            Logger().error("Attempted to add owner to non-existent device: %s", device_id)
            return False

        # Get current owner
        current_owner = session.exec(
            select(User).where(User.username == current_owner_username)
        ).first()

        if not current_owner:
            return False

        # Verify current owner has access
        current_link = session.exec(
            select(UserDeviceLink).where(
                UserDeviceLink.user_id == current_owner.id,
                UserDeviceLink.device_id == device.id,
            )
        ).first()

        if not current_link:
            return False  # Current user is not an owner

        # Get new owner
        new_owner = session.exec(
            select(User).where(User.username == new_owner_username)
        ).first()

        if not new_owner:
            return False

        # Check if already linked
        existing_link = session.exec(
            select(UserDeviceLink).where(
                UserDeviceLink.user_id == new_owner.id, UserDeviceLink.device_id == device.id
            )
        ).first()

        if existing_link:
            return True  # Already linked

        # Create new link
        link = UserDeviceLink(user_id=new_owner.id, device_id=device.id)
        session.add(link)
        session.commit()
        return True


def update_device_status(
    device_id: str, status: str, last_seen: Optional[datetime] = None
) -> bool:
    """Update device status (called by the device itself or system)"""
    with Session(engine) as session:
        device = session.exec(select(Device).where(Device.device_id == device_id)).first()

        if not device:
            Logger().error("Attempted to update status of non-existent device: %s", device_id)
            return False

        device.status = status
        if last_seen:
            device.last_seen = last_seen

        session.add(device)
        session.commit()
        return True


def update_device_api_key(device_id: str, api_key: str) -> bool:
    """Update device API key for authentication"""
    with Session(engine) as session:
        device = session.exec(select(Device).where(Device.device_id == device_id)).first()

        if not device:
            Logger().error("Attempted to update API key of non-existent device: %s", device_id)
            return False

        device.api_key = api_key
        session.add(device)
        session.commit()
        return True


def verify_device_api_key(device_id: str, api_key: str) -> bool:
    """Verify that the provided API key matches the device's stored key"""
    with Session(engine) as session:
        device = session.exec(select(Device).where(Device.device_id == device_id)).first()

        if not device:
            Logger().warning("API key verification failed: unknown device_id %s", device_id)
            return False

        if not device.api_key:
            return False

        return device.api_key == api_key
