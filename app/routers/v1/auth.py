"""https://github.com/tiangolo/fastapi/issues/3303"""
from fastapi import APIRouter, Depends, status

from app.auth.forms import OAuth2PasswordAndRefreshRequestForm
from app.auth.password import verify_password
from app.auth.token import create_access_token, create_refresh_token  # type: ignore
from app.auth.users import get_current_active_basic_user_from_refresh_token
from app.crud.users import async_get_user_db
from app.models.token import Token
from app.models.users import BasicUser
from app.routers.http_exceptions import UnauthorizedHTTPException


async def authenticate_user(username: str, password: str) -> BasicUser:
    user_db = await async_get_user_db(username)
    if not user_db:
        raise UnauthorizedHTTPException(f"User :{username}: not found.")
    if not verify_password(password, user_db.hashed_password):
        raise UnauthorizedHTTPException("Incorrect username or password.")

    return user_db


router = APIRouter()


# provide a method to create access tokens. The create_access_token()
# function is used to actually generate the token to use authorization
# later in endpoint protected
@router.post(
    '/token',
    status_code=status.HTTP_200_OK,
    description="Login and get an access token.",
    response_description="A :Token: model.",
    response_model=Token,
    responses={
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response
    }
)
async def login_for_tokens(
    form_data: OAuth2PasswordAndRefreshRequestForm = Depends()
):
    if form_data.grant_type == "refresh_token":
        user = await get_current_active_basic_user_from_refresh_token(
            form_data.refresh_token
        )
    else:
        user = await authenticate_user(form_data.username, form_data.password)

    # subject identifier for who this token is for example id or username from DB
    access_token = create_access_token(user.username)
    refresh_token = create_refresh_token(user.username)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )
