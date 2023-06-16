"""Based on https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/"""
from datetime import datetime
from typing import Literal, cast

from fastapi import Depends
from jose import JWTError, jwt

from app.config.auth import get_oauth2_scheme
from app.config.settings import get_settings
from app.config.variables import Security as VarConfig  # type: ignore
from app.crud.users import async_get_user_db
from app.models.token import TokenData
from app.models.users import BasicUser
from app.routers.http_exceptions import (
    BadRequestHTTPException, UnauthorizedHTTPException,
)


def _get_token_data(
    token: str,
    token_type: Literal["access", "refresh"],
) -> TokenData:
    exc_detail: str = "Could not validate credentials."
    try:
        payload: dict[str, str | datetime] = jwt.decode(
            token,
            get_settings().SECRET_KEY,
            algorithms=[VarConfig.ALGORITHM]
        )
        if payload.get("type") != token_type:
            UnauthorizedHTTPException(f"Token of type :{token_type}: required.")
        username = cast(str, payload.get("sub"))
        if username is None:
            raise UnauthorizedHTTPException(exc_detail)
        token_data = TokenData(username=username)
    except JWTError:
        raise UnauthorizedHTTPException(exc_detail)

    return token_data


async def get_current_active_basic_user(
    token: str = Depends(get_oauth2_scheme())
) -> BasicUser:
    token_data = _get_token_data(token, 'access')
    user = await async_get_user_db(username=token_data.username)
    if user is None:
        raise UnauthorizedHTTPException(f"User :{token_data.username}: not found.")
    if user.disabled:
        raise BadRequestHTTPException(f"User :{token_data.username}: is inactive.")

    return user


async def get_current_active_basic_user_from_refresh_token(
    refresh_token: str
) -> BasicUser:
    token_data = _get_token_data(refresh_token, 'refresh')
    user = await async_get_user_db(username=token_data.username)
    if user is None:
        raise UnauthorizedHTTPException(f"User :{token_data.username}: not found.")
    if user.disabled:
        raise BadRequestHTTPException(f"User :{token_data.username}: is inactive.")

    return user
