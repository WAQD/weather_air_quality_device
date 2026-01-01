from typing import List, Optional

from sqlmodel import Session, select

from waqd_website.database import User, engine
from waqd.base.translation import Translation
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
