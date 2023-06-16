from fastapi import APIRouter, Depends, status

from app.auth.users import get_current_active_basic_user
from app.models.users import BasicUser
from app.routers.http_exceptions import UnauthorizedHTTPException

router = APIRouter()


@router.get(
    "/me/",
    status_code=status.HTTP_200_OK,
    response_model=BasicUser,
    response_description="A :BasicUser: model",
    responses={
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response
    }
)
async def my_user(user: BasicUser = Depends(get_current_active_basic_user)):
    return user
