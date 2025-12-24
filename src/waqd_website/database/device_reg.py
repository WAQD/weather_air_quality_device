import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from waqd_website.database import (
    Device,
    DeviceRegistrationSession,
    RegistrationStatus,
    User,
    UserDeviceLink,
    engine,
)


def generate_passphrase() -> str:
    """
    Generate a secure 6-character passphrase
    Excludes ambiguous characters: 0, O, I, l, 1
    """
    charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(charset) for _ in range(6))


def create_registration_session(device_id: str, location: str) -> DeviceRegistrationSession:
    """Create a new device registration session"""
    with Session(engine) as session:
        # Expire any existing sessions for this device
        existing_sessions = session.exec(
            select(DeviceRegistrationSession).where(
                DeviceRegistrationSession.device_id == device_id,
                DeviceRegistrationSession.status
                in ([RegistrationStatus.PENDING, RegistrationStatus.CLAIMED]),
            )
        ).all()

        for old_session in existing_sessions:
            old_session.status = RegistrationStatus.EXPIRED
            session.add(old_session)

        # Create new session
        session_id = str(uuid.uuid4())
        passphrase = generate_passphrase()
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        new_session = DeviceRegistrationSession(
            session_id=session_id,
            device_id=device_id,
            passphrase=passphrase,
            status=RegistrationStatus.PENDING,
            expires_at=expires_at,
            location=location,
        )

        session.add(new_session)
        session.commit()
        session.refresh(new_session)
        return new_session


def get_session_by_passphrase(passphrase: str) -> Optional[DeviceRegistrationSession]:
    """Get a registration session by passphrase"""
    with Session(engine) as session:
        statement = select(DeviceRegistrationSession).where(
            DeviceRegistrationSession.passphrase == passphrase.upper()
        )
        return session.exec(statement).first()


def get_session_by_id(session_id: str) -> Optional[DeviceRegistrationSession]:
    """Get a registration session by session_id"""
    with Session(engine) as session:
        statement = select(DeviceRegistrationSession).where(
            DeviceRegistrationSession.session_id == session_id
        )
        return session.exec(statement).first()


def claim_session(passphrase: str, user_id: int) -> Optional[str]:
    """
    Claim a registration session with a passphrase
    Returns session_id if successful, None if failed
    """
    with Session(engine) as session:
        reg_session = session.exec(
            select(DeviceRegistrationSession).where(
                DeviceRegistrationSession.passphrase == passphrase.upper(),
                DeviceRegistrationSession.status == RegistrationStatus.PENDING,
            )
        ).first()

        if not reg_session:
            return None

        # Check if expired
        if reg_session.expires_at < datetime.utcnow():
            reg_session.status = RegistrationStatus.EXPIRED
            session.add(reg_session)
            session.commit()
            return None

        # Claim the session
        reg_session.status = RegistrationStatus.CLAIMED
        reg_session.requesting_user_id = user_id
        reg_session.claimed_at = datetime.utcnow()

        session.add(reg_session)
        session.commit()
        return reg_session.session_id


def confirm_registration(session_id: str, approved: bool) -> Optional[Device]:
    """
    Confirm or reject a registration session
    If approved, creates Device and links to user
    """
    with Session(engine) as session:
        reg_session = session.exec(
            select(DeviceRegistrationSession).where(
                DeviceRegistrationSession.session_id == session_id
            )
        ).first()

        if not reg_session:
            return None

        if not approved:
            reg_session.status = RegistrationStatus.REJECTED
            session.add(reg_session)
            session.commit()
            return None

        # Check if claimed and not expired
        if reg_session.status != RegistrationStatus.CLAIMED:
            return None

        if reg_session.expires_at < datetime.utcnow():
            reg_session.status = RegistrationStatus.EXPIRED
            session.add(reg_session)
            session.commit()
            return None

        # Get the user
        user = session.get(User, reg_session.requesting_user_id)
        if not user:
            return None

        # Check if device already exists
        existing_device = session.exec(
            select(Device).where(Device.device_id == reg_session.device_id)
        ).first()

        if existing_device:
            # Device exists, just add user as owner
            device = existing_device

            # Check if link already exists
            existing_link = session.exec(
                select(UserDeviceLink).where(
                    UserDeviceLink.user_id == user.id, UserDeviceLink.device_id == device.id
                )
            ).first()

            if not existing_link:
                link = UserDeviceLink(user_id=user.id, device_id=device.id)
                session.add(link)
        else:
            # Create new device
            device = Device(
                device_id=reg_session.device_id,
                name=f"WAQD-{reg_session.device_id[-6:]}",
                status="offline",
                location=reg_session.location,
            )
            session.add(device)
            session.flush()  # Get device.id

            # Link to user
            link = UserDeviceLink(user_id=user.id, device_id=device.id)
            session.add(link)

        # Update session status
        reg_session.status = RegistrationStatus.APPROVED
        session.add(reg_session)

        session.commit()
        session.refresh(device)
        return device


def expire_old_sessions():
    """Expire all sessions past their expiration time"""
    with Session(engine) as session:
        expired_sessions = session.exec(
            select(DeviceRegistrationSession).where(
                DeviceRegistrationSession.expires_at < datetime.utcnow(),
                DeviceRegistrationSession.status
                in ([RegistrationStatus.PENDING, RegistrationStatus.CLAIMED]),
            )
        ).all()

        for reg_session in expired_sessions:
            reg_session.status = RegistrationStatus.EXPIRED
            session.add(reg_session)

        session.commit()
        return len(expired_sessions)
