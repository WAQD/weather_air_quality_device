from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated, Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.openapi.models import OAuthFlows, OAuthFlowPassword
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from waqd_website.database import User
from waqd_website.database.config import get_or_create_jwt_secret
from waqd_website.database.user import get_user_by_username

# Load or create persistent JWT secret from database
USER_SESSION_SECRET = get_or_create_jwt_secret()


class RequiresLoginException(StarletteHTTPException):
    pass


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 1
ADMIN_PERMISSION = "users:admin"

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
    expires: datetime | None = None


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=12,
    bcrypt__min_rounds=10,
)


class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: str | None = None,
        scopes: dict | None = None,
        auto_error: bool = True,
    ):
        flows = OAuthFlows(password=OAuthFlowPassword(tokenUrl=tokenUrl))
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        header_authorization: str = request.headers.get("Authorization", "")
        cookie_authorization: str = request.cookies.get("Authorization", "")
        header_scheme, header_param = get_authorization_scheme_param(header_authorization)
        cookie_scheme, cookie_param = get_authorization_scheme_param(cookie_authorization)

        if header_scheme.lower() == "bearer":
            authorization = True
            scheme = header_scheme
            param = header_param

        elif cookie_scheme.lower() == "bearer":
            authorization = True
            scheme = cookie_scheme
            param = cookie_param
        else:
            authorization = False

        if not authorization or scheme.lower() != "bearer":
            return None
        return param


oauth2_scheme = OAuth2PasswordBearerWithCookie(
    tokenUrl="/token",
    scopes={
        "me": "diagnostics about the current user",
        "bgp": "capabilities about bgp route lookup",
    },
)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user_from_token(token_data: TokenData):
    if token_data.username:
        return get_user_by_username(token_data.username)
    return None


def get_user_from_name(username: str):
    return get_user_by_username(username)


def authenticate_user(username: str, password: str):
    user = get_user_from_name(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, USER_SESSION_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


@lru_cache(maxsize=None)
def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, USER_SESSION_SECRET, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(
            username=username,
            expires=datetime.fromtimestamp(payload.get("exp", 0), timezone.utc),
        )
        return token_data
    except InvalidTokenError:
        return None


def get_current_user(token):
    if not token:
        return None

    token_data = decode_access_token(token)
    if token_data is None:
        return None
    # check validity
    if token_data.expires is None or token_data.expires < datetime.now(timezone.utc):
        return None
    return get_user_from_token(token_data)


async def get_current_user_with_exception(token: Annotated[str, Depends(oauth2_scheme)]):
    user = get_current_user(token)
    if user is None:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        raise credentials_exception
    return user


async def get_current_user_with_redirect(
    request: Request, token: Annotated[str, Depends(oauth2_scheme)]
):
    for open_routes in ["/public/", "/static/"]:
        if request.url.path.startswith(open_routes):
            return None
    user = get_current_user(token)
    if user is None:
        raise RequiresLoginException(status.HTTP_303_SEE_OTHER)
    return user


async def get_current_user_plain(token: Annotated[str, Depends(oauth2_scheme)]):
    user = get_current_user(token)
    return user


class PermissionChecker:
    def __init__(self, required_permissions: list[str]) -> None:
        self.required_permissions = required_permissions

    def __call__(self, _user: User = Depends(get_current_user_plain), exception=True) -> bool:
        # update from db
        user = get_user_from_name(_user.username)
        assert user is not None
        if self.check_permissions(user):
            return True
        if exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Permissions")
        return False

    def get_permissions(self, user: User) -> list[str]:
        return user.permissions

    def check_permissions(self, user: User) -> bool:
        for r_perm in self.required_permissions:
            if r_perm not in user.permissions:
                return False
        return True


user_exception_check = Depends(get_current_user_with_exception)
user_redirect_check = Depends(get_current_user_with_redirect)
user_plain_check = Depends(get_current_user_plain)

admin_check = Depends(PermissionChecker(required_permissions=[ADMIN_PERMISSION]))
