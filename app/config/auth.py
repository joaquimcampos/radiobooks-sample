from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.config.logging import LoggerValueError, get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)


class AuthState():
    def __init__(self) -> None:
        self.pwd_context: CryptContext | None = None
        self.oauth2_scheme: OAuth2PasswordBearer | None = None


_AUTH_STATE: AuthState | None = None


def init_authorization():
    global _AUTH_STATE
    _AUTH_STATE = AuthState()
    _AUTH_STATE.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if (version := get_settings().API_VERSION) == "v1":
        _AUTH_STATE.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
    else:
        raise LoggerValueError(logger, f"API version {version} is not available.")


def get_pwd_context() -> CryptContext:
    if _AUTH_STATE is None or _AUTH_STATE.pwd_context is None:
        init_authorization()
    assert _AUTH_STATE and _AUTH_STATE.pwd_context
    return _AUTH_STATE.pwd_context


def get_oauth2_scheme() -> OAuth2PasswordBearer:
    if _AUTH_STATE is None or _AUTH_STATE.oauth2_scheme is None:
        init_authorization()
    assert _AUTH_STATE and _AUTH_STATE.oauth2_scheme
    return _AUTH_STATE.oauth2_scheme
