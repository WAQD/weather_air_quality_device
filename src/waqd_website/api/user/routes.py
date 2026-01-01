import secrets
from typing import Annotated
from fastapi import APIRouter
from pydantic import BaseModel

from waqd_website.auth.authentication import User, user_exception_check, admin_check
from waqd_website.database.user import (
    get_all_users,
    delete_user,
    add_user,
    update_user_password,
    update_user_email,
    update_user_username,
    get_user_by_username,
)
from fastapi import HTTPException, status

rt = APIRouter()


class UserInfo(BaseModel):
    username: str
    email: str | None = None
    permissions: list[str]


class UserListItem(BaseModel):
    username: str
    permissions: list[str]


@rt.get("/me", response_model=UserInfo)
async def get_current_user(current_user: Annotated[User, user_exception_check]):
    """Get current logged-in user information"""
    return UserInfo(
        username=current_user.username,
        email=current_user.email,
        permissions=current_user.permissions
    )


@rt.get("/admin/users", response_model=list[UserListItem])
async def list_users(current_user: Annotated[User, admin_check]):
    """List all users (admin only)"""
    users = get_all_users()
    return [
        UserListItem(username=user.username, permissions=user.permissions) for user in users
    ]


## add user
@rt.post("/admin/users", response_model=UserListItem)
async def add_user_endpoint(
    user_info: UserListItem, current_user: Annotated[User, admin_check]
):
    """Add a new user (admin only)"""

    user = add_user(
        username=user_info.username,
        password=hex(secrets.randbits(64))[2:],  # random password
        permissions=user_info.permissions,
    )
    return UserListItem(username=user.username, permissions=user.permissions)


## delete user
@rt.delete("/admin/users/{username}", response_model=dict)
async def delete_user_endpoint(username: str, current_user: Annotated[User, admin_check]):
    """Delete a user (admin only)"""

    success = delete_user(username)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"detail": "User deleted successfully"}


# set password
@rt.put("/users/{username}/password", response_model=dict)
async def set_user_password_endpoint(
    username: str, password_info: dict, current_user: Annotated[User, user_exception_check]
):
    """Set a user's password (self or admin)"""

    if current_user.username != username and "users:admin" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to change this user's password",
        )

    new_password = password_info.get("new_password")
    if not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="New password not provided"
        )

    success = update_user_password(username, new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"detail": "Password updated successfully"}


# update email
@rt.put("/users/{username}/email", response_model=dict)
async def set_user_email_endpoint(
    username: str, email_info: dict, current_user: Annotated[User, user_exception_check]
):
    """Update a user's email (self or admin)"""

    if current_user.username != username and "users:admin" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to change this user's email",
        )

    email = email_info.get("email")
    
    # Check if email is already taken by another user
    if email:
        existing_user = get_user_by_username(username)
        if not existing_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # Check if email is taken by another user
        from waqd_website.database import User as DBUser, engine
        from sqlmodel import Session, select
        with Session(engine) as session:
            statement = select(DBUser).where(DBUser.email == email)
            user_with_email = session.exec(statement).first()
            if user_with_email and user_with_email.username != username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use by another user"
                )

    success = update_user_email(username, email)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"detail": "Email updated successfully"}


# update username
@rt.put("/users/{username}/username", response_model=dict)
async def set_user_username_endpoint(
    username: str, username_info: dict, current_user: Annotated[User, user_exception_check]
):
    """Update a user's username (self or admin)"""

    if current_user.username != username and "users:admin" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to change this user's username",
        )

    new_username = username_info.get("new_username")
    if not new_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="New username not provided"
        )

    # Check if new username is already taken
    existing_user = get_user_by_username(new_username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    success = update_user_username(username, new_username)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"detail": "Username updated successfully"}
