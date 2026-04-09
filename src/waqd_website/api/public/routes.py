from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse

import waqd
from waqd_website.auth.authentication import (
    TOKEN_EXPIRE_LONG_DAYS,
    TOKEN_EXPIRE_SHORT_MINUTES,
    Token,
    User,
    authenticate_user,
    create_access_token,
    decode_access_token,
    oauth2_scheme,
    user_exception_check,
)

# Refresh threshold for short-lived tokens (refresh in last 30 min of 2h window)
TOKEN_REFRESH_THRESHOLD_SHORT_MINUTES = 30
# Refresh threshold for long-lived tokens (refresh in last 7 days of 30-day window)
TOKEN_REFRESH_THRESHOLD_LONG_DAYS = 7


class LoginForm:
    def __init__(
        self,
        username: str = Form(...),
        password: str = Form(...),
        grant_type: str = Form(default="password"),
        remember_me: bool = Form(default=False),
    ):
        self.username = username
        self.password = password
        self.grant_type = grant_type
        self.remember_me = remember_me

rt = APIRouter()

current_path = Path(__file__).parent.resolve()

@rt.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[LoginForm, Depends()], request: Request
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if form_data.remember_me:
        access_token_expires = timedelta(days=TOKEN_EXPIRE_LONG_DAYS)
    else:
        access_token_expires = timedelta(minutes=TOKEN_EXPIRE_SHORT_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "remember": form_data.remember_me},
        expires_delta=access_token_expires,
    )
    response = JSONResponse(
        {"access_token": access_token, "token_type": "bearer"},
        status_code=status.HTTP_200_OK,
    )
    set_access_token_cookie(response, access_token, access_token_expires, request)
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
    
    # Refresh token if close to expiry; threshold depends on token type
    if token_data.remember_me:
        refresh_threshold = timedelta(days=TOKEN_REFRESH_THRESHOLD_LONG_DAYS)
        new_expiry = timedelta(days=TOKEN_EXPIRE_LONG_DAYS)
    else:
        refresh_threshold = timedelta(minutes=TOKEN_REFRESH_THRESHOLD_SHORT_MINUTES)
        new_expiry = timedelta(minutes=TOKEN_EXPIRE_SHORT_MINUTES)

    time_until_expiry = token_expires - datetime.now(timezone.utc)
    if time_until_expiry < refresh_threshold:
        access_token = create_access_token(
            data={"sub": current_user.username, "remember": token_data.remember_me},
            expires_delta=new_expiry,
        )
        response = JSONResponse(
            {"access_token": access_token, "token_type": "bearer"},
            status_code=status.HTTP_200_OK,
        )
        set_access_token_cookie(response, access_token, new_expiry, request)
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
    response: JSONResponse, access_token: str, access_token_expires: timedelta, request: Request
):
    secure = is_https(request)
    if waqd.DEBUG_LEVEL > 0:
        secure = False

    response.set_cookie(
        key="Authorization",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=int(access_token_expires.total_seconds()),
        # Use an absolute expiry datetime for broad browser compatibility.
        # Some clients treat numeric/relative expires values as invalid,
        # which can degrade this into a session cookie (especially in PWAs).
        expires=datetime.now(timezone.utc) + access_token_expires,
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


