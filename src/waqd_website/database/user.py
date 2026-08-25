import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from email_validator import EmailNotValidError, validate_email
from sqlmodel import Session, select

from waqd_website.database import EmailVerificationToken, PasswordResetToken, User, engine
from waqd.components.translation import Translation
from waqd_website.mail.mail import send_email


def add_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    permissions: Optional[List[str]] = None,
):
    # avoid dependency loop
    from waqd_website.auth.authentication import get_password_hash

    hashed_password = get_password_hash(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        permissions=permissions or [],
    )
    with Session(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)

    # Send welcome email if email is provided
    if email:
        try:
            translation = Translation()
            subject = translation.get_localized_string("ui_dict.json", "welcome_email_subject")
            body_template = translation.get_localized_string(
                "ui_dict.json", "welcome_email_body"
            )
            body = body_template.format(username=username)
            send_email(email, subject, body)
        except Exception as e:
            # Log error but don't fail the user creation
            print(f"Failed to send welcome email to {email}: {e}")

    return user


def delete_user(username: str) -> bool:
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        if not user:
            return False
        session.delete(user)
        session.commit()
    return True


def get_user_by_username(username: str) -> Optional[User]:
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        return user


def get_user_by_id(user_id: int) -> Optional[User]:
    with Session(engine) as session:
        statement = select(User).where(User.id == user_id)
        user = session.exec(statement).first()
        return user


def get_all_users() -> List[User]:
    """Get all users from the database"""
    with Session(engine) as session:
        statement = select(User)
        users = session.exec(statement).all()
        return list(users)


def update_user_password(username: str, new_password: str) -> bool:
    from waqd_website.auth.authentication import get_password_hash

    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        if not user:
            return False
        user.hashed_password = get_password_hash(new_password)
        session.add(user)
        session.commit()
        # Get email before session closes
        user_email = user.email

    # Send password change notification if user has email
    if user_email:
        try:
            translation = Translation()
            subject = translation.get_localized_string(
                "ui_dict.json", "password_changed_email_subject"
            )
            body_template = translation.get_localized_string(
                "ui_dict.json", "password_changed_email_body"
            )
            body = body_template.format(username=username)
            send_email(user_email, subject, body)
        except Exception as e:
            # Log error but don't fail the password update
            print(f"Failed to send password change email to {user_email}: {e}")

    return True


def update_user_email(username: str, email: Optional[str]) -> bool:
    """Update a user's email address"""

    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        if not user:
            return False

        old_email = user.email
        user.email = email
        session.add(user)
        session.commit()

    # Send email change notification to the old email address if it exists
    if old_email:
        try:
            translation = Translation()
            subject = translation.get_localized_string(
                "ui_dict.json", "email_changed_email_subject"
            )
            body_template = translation.get_localized_string(
                "ui_dict.json", "email_changed_email_body"
            )
            body = body_template.format(username=username, new_email=email or "none")
            send_email(old_email, subject, body)
        except Exception as e:
            # Log error but don't fail the email update
            print(f"Failed to send email change notification to {old_email}: {e}")

    return True


def update_user_username(old_username: str, new_username: str) -> bool:
    """Update a user's username"""

    with Session(engine) as session:
        statement = select(User).where(User.username == old_username)
        user = session.exec(statement).first()
        if not user:
            return False
        user.username = new_username
        session.add(user)
        session.commit()
        # Get email before session closes
        user_email = user.email

    # Send username change notification if user has email
    if user_email:
        try:
            translation = Translation()
            subject = translation.get_localized_string(
                "ui_dict.json", "username_changed_email_subject"
            )
            body_template = translation.get_localized_string(
                "ui_dict.json", "username_changed_email_body"
            )
            body = body_template.format(old_username=old_username, new_username=new_username)
            send_email(user_email, subject, body)
        except Exception as e:
            # Log error but don't fail the username update
            print(f"Failed to send username change email to {user_email}: {e}")

    return True


_RESET_TOKEN_EXPIRY_MINUTES = 30
_VERIFICATION_TOKEN_EXPIRY_MINUTES = 30


def normalize_email(email: str) -> str:
    try:
        return validate_email(email.strip(), check_deliverability=False).normalized
    except EmailNotValidError as exc:
        raise ValueError("Invalid email address") from exc


def register_user(username: str, password: str, email: str) -> tuple[User, str]:
    """Create an unverified user and return the user plus a raw verification token."""
    from waqd_website.auth.authentication import get_password_hash

    username = username.strip()
    email = normalize_email(email)
    if not username or len(username) > 255:
        raise ValueError("Invalid username")
    if len(email) > 255:
        raise ValueError("Invalid email address")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=_VERIFICATION_TOKEN_EXPIRY_MINUTES
    )
    with Session(engine) as session:
        if session.exec(select(User).where(User.username == username)).first():
            raise ValueError("Username or email already registered")
        if session.exec(select(User).where(User.email == email)).first():
            raise ValueError("Username or email already registered")
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            email_verification_required=True,
        )
        session.add(user)
        session.flush()
        session.add(
            EmailVerificationToken(
                token_hash=token_hash,
                user_id=user.id,  # type: ignore[arg-type]
                email=email,
                expires_at=expires_at,
            )
        )
        session.commit()
        session.refresh(user)
    return user, raw_token


def create_email_verification_token(user_id: int, email: str) -> str:
    """Create a hashed, single-use verification token for an email address."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=_VERIFICATION_TOKEN_EXPIRY_MINUTES
    )
    with Session(engine) as session:
        old_tokens = session.exec(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used == False,  # noqa: E712
            )
        ).all()
        for token in old_tokens:
            token.used = True
            session.add(token)
        session.add(
            EmailVerificationToken(
                token_hash=token_hash,
                user_id=user_id,
                email=normalize_email(email),
                expires_at=expires_at,
            )
        )
        session.commit()
    return raw_token


def consume_email_verification_token(raw_token: str) -> bool:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with Session(engine) as session:
        record = session.exec(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash
            )
        ).first()
        if record is None or record.used:
            return False
        if record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return False
        user = session.exec(select(User).where(User.id == record.user_id)).first()
        if user is None or normalize_email(user.email or "") != normalize_email(record.email):
            return False
        user.email_verified_at = datetime.now(timezone.utc)
        user.email_verification_required = False
        record.used = True
        session.add(user)
        session.add(record)
        session.commit()
    return True


def get_user_by_email(email: str) -> Optional[User]:
    with Session(engine) as session:
        statement = select(User).where(User.email == email)
        return session.exec(statement).first()


def create_password_reset_token(user_id: int) -> str:
    """Generate a raw reset token, store its SHA-256 hash, and return the raw token."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_RESET_TOKEN_EXPIRY_MINUTES)
    with Session(engine) as session:
        # Invalidate any existing unused tokens for this user
        old_tokens = session.exec(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used == False,  # noqa: E712
            )
        ).all()
        for token in old_tokens:
            token.used = True
            session.add(token)
        session.add(
            PasswordResetToken(token_hash=token_hash, user_id=user_id, expires_at=expires_at)
        )
        session.commit()
    return raw_token


def get_or_create_widget_key(user_id: int) -> str:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if user is None:
            raise ValueError(f"User {user_id} not found")
        if user.widget_key:
            return user.widget_key
        user.widget_key = secrets.token_hex(64)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.widget_key


def get_user_by_widget_key(widget_key: str) -> Optional[User]:
    with Session(engine) as session:
        statement = select(User).where(User.widget_key == widget_key)
        return session.exec(statement).first()


def consume_password_reset_token(raw_token: str, new_password: str) -> bool:
    """Validate the token, reset the password, and mark the token used.
    Returns True on success, False if the token is invalid/expired/already used."""
    from waqd_website.auth.authentication import get_password_hash

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with Session(engine) as session:
        record = session.exec(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        ).first()
        if record is None or record.used:
            return False
        if record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return False
        user = session.exec(select(User).where(User.id == record.user_id)).first()
        if user is None:
            return False
        user.hashed_password = get_password_hash(new_password)
        record.used = True
        session.add(user)
        session.add(record)
        session.commit()
    return True
