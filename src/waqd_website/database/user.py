from typing import List, Optional

from sqlmodel import Session, select

from waqd_website.database import User, engine


def add_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    permissions: Optional[List[str]] = None,
):
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
    return True
