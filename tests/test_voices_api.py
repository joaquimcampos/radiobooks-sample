import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


@pytest.fixture
def sample_lang() -> dict[str, str]:
    return {"name": "a language name", "display_name": "a display name"}


async def test_get_langs(
    version: str,
    client: AsyncClient,
    sample_lang: dict[str, str]
):
    response = await client.get(f"/api/{version}/languages")
    assert response.status_code == status.HTTP_200_OK
    assert sample_lang in response.json()


async def test_get_voices_for_lang_bad_request(version: str, client: AsyncClient):
    response = await client.get(
        f"/api/{version}/languages/an-invalid-language-name/voices"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
