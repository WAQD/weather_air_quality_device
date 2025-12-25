from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

import waqd
from waqd_website.auth.authentication import (
    ACCESS_TOKEN_EXPIRE_DAYS,
    Token,
    User,
    authenticate_user,
    create_access_token,
    decode_access_token,
    oauth2_scheme,
    user_exception_check,
)

rt = APIRouter()

current_path = Path(__file__).parent.resolve()

@rt.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], request: Request
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response = JSONResponse(
        {"access_token": access_token, "token_type": "bearer"},
        status_code=status.HTTP_200_OK,
    )
    set_access_token_cookie(response, user.username, access_token, request)
    return response


@rt.get("/keepalive", response_class=JSONResponse)
async def keepalive(
    current_user: Annotated[User, user_exception_check],
    token: Annotated[str, Depends(oauth2_scheme)],
    request: Request,
):
    # Extract expiration from the current token
    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    token_expires = token_data.expires
    if token_expires is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    # Refresh token if it expires in less than 11 minutes
    time_until_expiry = token_expires - datetime.now(timezone.utc)
    if time_until_expiry < timedelta(minutes=11):
        access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        access_token = create_access_token(
            data={"sub": current_user.username}, expires_delta=access_token_expires
        )
        response = JSONResponse(
            {"access_token": access_token, "token_type": "bearer"},
            status_code=status.HTTP_200_OK,
        )
        set_access_token_cookie(response, current_user.username, access_token, request)
        return response
    
    # Token is still valid, return success without refreshing
    return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)


def is_https(request: Request) -> bool:
    # Direct HTTPS
    if request.url.scheme == "https":
        return True
    # Behind a reverse proxy that sets X-Forwarded-Proto
    proto = request.headers.get("x-forwarded-proto", "")
    return "https" in proto.split(",")


def set_access_token_cookie(
    response: JSONResponse, username: str, access_token: str, request: Request
):
    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    if not access_token:
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )

    secure = is_https(request)
    # Optional: override for debugging
    if waqd.DEBUG_LEVEL > 0:
        secure = False

    response.set_cookie(
        key="Authorization",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=int(access_token_expires.total_seconds()),
        expires=int(access_token_expires.total_seconds()),
        samesite="lax",
        secure=secure,
    )
    return response


@rt.post("/logout", response_class=JSONResponse)
async def logout(request: Request):
    """Logout endpoint that deletes the session cookie"""
    response = JSONResponse(
        {"detail": "Logged out successfully"}, status_code=status.HTTP_200_OK
    )
    
    secure = is_https(request)
    # Optional: override for debugging
    if waqd.DEBUG_LEVEL > 0:
        secure = False
    
    # Delete the Authorization cookie
    response.delete_cookie(
        key="Authorization",
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    return response


