"""
Based on:
https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
https://github.com/tiangolo/fastapi/issues/3303
"""
import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config.settings import get_settings
from app.config.variables import Security as VarConfig  # type: ignore


class MyAuthJWT:

    @classmethod
    def create_token(
        cls,
        subject: str,
        type_token: str,
        expiration_timedelta: timedelta
    ) -> str:
        """
        Create token for access_token and refresh_token (utf-8)

        :param subject: Identifier for who this token is (username).
        :param type_token: indicate token is access_token or refresh_token
        :param exp_time: Set the duration of the JWT

        :return: Encoded token
        """
        # Validation type data
        if not isinstance(subject, (str, int)):
            raise TypeError("subject must be a string or integer")

        # Data section
        reserved_claims = {
            "sub": subject,
            "iat": cls._get_int_from_datetime(datetime.now(timezone.utc)),
            "nbf": cls._get_int_from_datetime(datetime.now(timezone.utc)),
            "jti": cls._get_jwt_identifier()
        }

        custom_claims = {"type": type_token}

        # for access_token only fresh needed
        reserved_claims['exp'] = (
            cls._get_int_from_datetime(datetime.now(timezone.utc)) +
            int(expiration_timedelta.total_seconds())
        )

        encoded_jwt: str = jwt.encode(
            {**reserved_claims, **custom_claims},
            get_settings().SECRET_KEY,
            algorithm=VarConfig.ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def _get_jwt_identifier() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _get_int_from_datetime(value: datetime) -> int:
        """
        :param value: datetime with or without timezone, if don't contains timezone
                      it will managed as it is UTC
        :return: Seconds since the Epoch
        """
        if not isinstance(value, datetime):  # pragma: no cover
            raise TypeError('a datetime is required')
        return int(value.timestamp())


def create_access_token(username: str) -> str:
    expiration_timedelta = timedelta(minutes=VarConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
    encoded_jwt = MyAuthJWT.create_token(
        subject=username,
        type_token="access",
        expiration_timedelta=expiration_timedelta,
    )
    return encoded_jwt
