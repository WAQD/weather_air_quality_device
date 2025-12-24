import secrets
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from waqd_website.database import ServerConfig, engine

# Server Configuration management functions


def get_config_value(key: str) -> Optional[str]:
    """Get a configuration value by key"""
    with Session(engine) as session:
        statement = select(ServerConfig).where(ServerConfig.key == key)
        config = session.exec(statement).first()
        return config.value if config else None


def set_config_value(key: str, value: str) -> None:
    """Set or update a configuration value"""
    with Session(engine) as session:
        statement = select(ServerConfig).where(ServerConfig.key == key)
        config = session.exec(statement).first()

        if config:
            config.value = value
            config.updated_at = datetime.utcnow()
            session.add(config)
        else:
            config = ServerConfig(key=key, value=value)
            session.add(config)

        session.commit()


def get_or_create_jwt_secret() -> str:
    """Get the JWT secret from database, or create one if it doesn't exist"""

    secret = get_config_value("jwt_secret")
    if not secret:
        secret = secrets.token_hex(32)
        set_config_value("jwt_secret", secret)
    return secret
