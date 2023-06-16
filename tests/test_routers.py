import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_http_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "OK"


async def test_db_health_check(client: AsyncClient):
    response = await client.get("/health/db")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "OK"
