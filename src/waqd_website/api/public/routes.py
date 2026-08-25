from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated
import os

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
from waqd_website.database.user import (
    consume_email_verification_token,
    consume_password_reset_token,
    create_email_verification_token,
    create_password_reset_token,
    get_user_by_email,
    register_user,
)
from waqd_website.mail.mail import send_reset_email, send_verification_email
from waqd_website.api.rate_limit import limiter

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


class SignupForm:
    def __init__(
        self,
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        password_confirmation: str = Form(...),
        accept_terms: bool = Form(...),
    ):
        self.username = username
        self.email = email
        self.password = password
        self.password_confirmation = password_confirmation
        self.accept_terms = accept_terms


rt = APIRouter()

current_path = Path(__file__).parent.resolve()


def public_base_url(request: Request) -> str:
    configured = os.getenv("WAQD_PUBLIC_URL", "").rstrip("/")
    if configured:
        return configured
    scheme = "https" if is_https(request) else "http"
    return f"{scheme}://{request.url.netloc}"


@rt.post("/signup", response_class=JSONResponse)
@limiter.limit("5/hour")
async def signup(form_data: Annotated[SignupForm, Depends()], request: Request):
    if not form_data.accept_terms:
        raise HTTPException(
            status_code=400, detail="Terms and privacy policy must be accepted."
        )
    if form_data.password != form_data.password_confirmation:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    try:
        user, raw_token = register_user(form_data.username, form_data.password, form_data.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    verification_url = f"{public_base_url(request)}/public/verify-email?token={raw_token}"
    if not send_verification_email(form_data.email.strip().lower(), verification_url):
        # Keep the account pending so a later resend can recover from a temporary
        # SMTP outage, but do not claim that the verification email was sent.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The account was created, but verification email delivery is "
                "currently unavailable. Please try again later."
            ),
        )
    return JSONResponse(
        {"detail": "Account created. Please check your email to verify your account."},
        status_code=status.HTTP_201_CREATED,
    )


@rt.post("/verify-email", response_class=JSONResponse)
@limiter.limit("20/hour")
async def verify_email(request: Request, token: str = Form(...)):
    if not consume_email_verification_token(token):
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")
    return JSONResponse(
        {"detail": "Email verified successfully."}, status_code=status.HTTP_200_OK
    )


@rt.post("/resend-verification", response_class=JSONResponse)
@limiter.limit("3/hour")
async def resend_verification(request: Request, email: str = Form(...)):
    normalized_email = email.strip().lower()
    user = get_user_by_email(normalized_email)
    if (
        user
        and user.id is not None
        and user.email_verification_required
        and not user.email_verified_at
    ):
        raw_token = create_email_verification_token(user.id, normalized_email)
        verification_url = f"{public_base_url(request)}/public/verify-email?token={raw_token}"
        send_verification_email(normalized_email, verification_url)
    return JSONResponse(
        {"detail": "If that email requires verification, a verification link has been sent."},
        status_code=status.HTTP_200_OK,
    )


@rt.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(form_data: Annotated[LoginForm, Depends()], request: Request):
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


@rt.post("/request-reset", response_class=JSONResponse)
@limiter.limit("5/hour")
async def request_password_reset(request: Request, email: str = Form(...)):
    """Request a password reset email. Always returns 200 to prevent user enumeration."""
    user = get_user_by_email(email)
    if user and user.id is not None:
        raw_token = create_password_reset_token(user.id)
        scheme = "https" if is_https(request) else "http"
        host = request.headers.get("x-forwarded-host") or request.url.netloc
        reset_url = f"{scheme}://{host}/public/reset-password?token={raw_token}"
        send_reset_email(email, reset_url)
    # Always return the same response to prevent email enumeration
    return JSONResponse(
        {"detail": "If that email is registered, a reset link has been sent."},
        status_code=status.HTTP_200_OK,
    )


@rt.post("/reset-password", response_class=JSONResponse)
async def reset_password(token: str = Form(...), new_password: str = Form(...)):
    """Consume a reset token and update the user's password."""
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )
    success = consume_password_reset_token(token, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token."
        )
    return JSONResponse(
        {"detail": "Password updated successfully."}, status_code=status.HTTP_200_OK
    )
