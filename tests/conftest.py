from typing import AsyncGenerator

import pytest
from httpx import AsyncClient

from app.config.settings import get_settings
from app.config.database import async_init_databases, async_drop_collections
from app.config.logging import get_logger
from app.config.aws import set_s3_workdir
from app.utils.aws import async_delete_s3_objs_in_prefix
from app.crud.users import async_add_user_db, async_delete_user_db_s3
from app.main import app


@pytest.fixture(
    scope="session",
    params=[
        pytest.param(
            ("asyncio", {"use_uvloop": True}),
            id="asyncio+uvloop",
        ),
    ]
)
def anyio_backend(request):
    return request.param


@pytest.fixture(scope="session")
def version() -> str:
    """API version"""
    return get_settings().API_VERSION


@pytest.fixture(scope="session")
def test_db_name() -> str:
    if not (db_name := get_settings().TEST_MONGO_DB):
        raise ValueError('Need to provide "TEST_MONGO_DB" env var.')

    return db_name


@pytest.fixture(scope="session")
def username() -> str:
    return 'test_user'


@pytest.fixture(scope="session")
def password() -> str:
    return 'test_password'


@pytest.fixture(scope="session")
async def client(
    version: str,
    test_db_name: str,
    username: str,
    password: str
) -> AsyncGenerator:
    async with AsyncClient(
        app=app,
        base_url="http://testserver",
    ) as client:
        # add user, get token. From https://github.com/rochacbruno/
        # fastapi-project-template/blob/main/tests/conftest.py#L56
        app.state.logger = get_logger(__name__)
        await async_init_databases(
            app.state,
            database_name=test_db_name
        )
        set_s3_workdir('tests')
        try:
            await async_add_user_db(username, password)
        except OSError:
            pass
        try:
            response = await client.post(
                f"/api/{version}/auth/token",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            token = response.json()["access_token"]
            client.headers["Authorization"] = f"Bearer {token}"

            yield client
        finally:
            if not await async_delete_user_db_s3(username):
                raise ValueError(f"User username :{username}: was not found.")
            await async_drop_collections()
            if not get_settings().LOCAL:
                await async_delete_s3_objs_in_prefix("")  # deleting in tests
