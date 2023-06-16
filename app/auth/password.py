"""Based on https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/"""
from app.config.auth import get_pwd_context


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_pwd_context().verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return get_pwd_context().hash(password)
