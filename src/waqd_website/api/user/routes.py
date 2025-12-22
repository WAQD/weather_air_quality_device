from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from waqd_website.auth.authentication import User, user_exception_check, admin_check
from waqd_website.database.db import get_all_users

rt = APIRouter()


class UserInfo(BaseModel):
    username: str
    permissions: list[str]


class UserListItem(BaseModel):
    username: str
    permissions: list[str]


@rt.get("/me", response_model=UserInfo)
async def get_current_user(current_user: Annotated[User, user_exception_check]):
    """Get current logged-in user information"""
    return UserInfo(
        username=current_user.username,
        permissions=current_user.permissions
    )


@rt.get("/admin/users", response_model=list[UserListItem])
async def list_users(current_user: Annotated[User, admin_check]):
    """List all users (admin only)"""
    users = get_all_users()
    return [
        UserListItem(
            username=user.username,
            permissions=user.permissions
        )
        for user in users
    ]
