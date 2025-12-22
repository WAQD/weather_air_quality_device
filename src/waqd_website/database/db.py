import os
from sqlmodel import SQLModel, Field, create_engine, Session, select
from passlib.context import CryptContext
from typing import Optional, List
from sqlalchemy import Column, JSON


password = os.getenv("DATABASE_PW", "waqd_root_pw")
# DATABASE_URL = f"mariadb+mariadbconnector://root:{password}@localhost:3306/waqd_userdata"
DATABASE_URL = "sqlite:///./waqd_userdata.db"  # SQLite for development
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=255)
    email: Optional[str] = Field(default=None, index=True, unique=True, max_length=255)
    hashed_password: str = Field(default=None, max_length=255)
    disabled: Optional[bool] = False
    permissions: List[str] = Field(default_factory=list, sa_column=Column(JSON, default=[]))


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SQLModel.metadata.create_all(engine)


def add_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
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


def get_user_by_username(username: str) -> Optional[User]:
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
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


# Uncomment to create admin user:
# add_user("admin", "admin123", email="admin@admin.com", permissions=["users:admin", "users:local"])
