from typing import Any
import pytest
from fastapi import status
import json
from pydantic import PositiveInt
from collections import OrderedDict
from httpx import AsyncClient
from app.models.fields import DocStatus, AudioStatus

pytestmark = pytest.mark.anyio


@pytest.fixture
def sample_item_info() -> dict[str, str]:
    return {
        "title": "A title",
        "author": "An author",
        "language_name": "A language name",
        "voice_name": "A voice name"
    }


# Utility function
def is_subset(mast_dict, subdict):
    for key, val in subdict.items():
        if isinstance(val, dict):
            if not (val.items() <= mast_dict[key].items()):
                return False
        elif isinstance(val, list):
            for i, element in enumerate(val):  # spans
                assert isinstance(element, dict)
                if not (element.items() <= mast_dict[key][i].items()):
                    return False
        else:
            if val != mast_dict[key]:
                return False

    return True


#############################################################
# Item

async def async_upload_item(
    version: str,
    client: AsyncClient,
    filename: str,
    cover: str,
    sample_item_info: dict[str, str],
    page_limit: PositiveInt | None = None
) -> dict[Any, Any]:
    # Post
    page_limit_query_str = f"?page_limit={page_limit}" if page_limit else ""
    response = await client.post(
        f"/api/{version}/items/{page_limit_query_str}",
        files={
            "file": open(filename, 'rb'),
            "cover": open(cover, 'rb')
        },
        data={"info": json.dumps(sample_item_info)}
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    item_dict = response.json()

    item_id = item_dict["_id"]
    response = await client.get(f"/api/{version}/items/{item_id}")
    assert response.status_code == status.HTTP_200_OK
    item_dict = response.json()
    assert item_dict['status'] == DocStatus.COMPLETED

    return item_dict


@pytest.mark.dependency(name="upload")
@pytest.mark.parametrize(
    ("filename, cover"), [('tests/data/sample.pdf', 'tests/data/sample.jpg')]
)
async def test_upload_item(
    version: str,
    client: AsyncClient,
    filename: str,
    cover: str,
    sample_item_info: dict[str, str],
    request
):
    item_dict = await async_upload_item(
        version, client, filename, cover, sample_item_info
    )
    item_id = item_dict["_id"]

    # Test fetching of document from (:start_page:, end_page]
    response = await client.get(
        f"/api/{version}/items/{item_id}/document?start_page=1&end_page=2",
    )
    assert response.status_code == status.HTTP_200_OK

    # Test fetching of full item document
    response = await client.get(f"/api/{version}/items/{item_id}/document")
    assert response.status_code == status.HTTP_200_OK

    # save for next test
    request.config.cache.set("item_dict", item_dict)
    request.config.cache.set("item_id", item_id)

    blocks = response.json()["blocks"]
    block_dict = OrderedDict([  # {block_id: read}
        (block["_id"],
         (True if "read" not in block else False))
        for block in blocks
    ])
    request.config.cache.set("block_dict", block_dict)

    # Test upload with page cut
    item_dict = await async_upload_item(
        version, client, filename, cover, sample_item_info, page_limit=1
    )
    item_id = item_dict["_id"]
    response = await client.get(f"/api/{version}/items/{item_id}/document")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["nb_pages"] == 1


# List items
@pytest.mark.dependency(depends=["upload"])
async def test_list_items(
    version: str,
    client: AsyncClient,
    request
):
    saved_item_dict = request.config.cache.get("item_dict", None)
    assert isinstance(saved_item_dict, dict)

    # List items
    response = await client.get(f"/api/{version}/items/")
    assert response.status_code == status.HTTP_200_OK
    item_dict = response.json()[0]  # get the first uploaded item ("sample.pdf")
    assert item_dict['status'] == DocStatus.COMPLETED
    assert item_dict == saved_item_dict


# Delete item
# https://pytest-order.readthedocs.io/en/stable/configuration.html#order-scope
@pytest.mark.dependency(depends=["upload"])
@pytest.mark.order("last")
async def test_delete_item(
    version: str,
    client: AsyncClient,
    request
):
    item_id = request.config.cache.get("item_id", None)

    # Delete item
    response = await client.delete(f"/api/{version}/items/{item_id}")
    assert response.status_code == status.HTTP_200_OK

    # check that item was deleted
    response = await client.get(f"/api/{version}/items/{item_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


#############################################################
# Audios

@pytest.mark.dependency(name="request_block_batch_audio", depends=["upload"])
async def test_request_block_batch_audio(
    version: str,
    client: AsyncClient,
    request
):
    item_id = request.config.cache.get("item_id", None)
    block_dict = request.config.cache.get("block_dict", None)
    audio_blocks_ids = list(block_dict.keys())[0:5]  # get audio for first 5 blocks

    # Post
    payload = {"block_ids": audio_blocks_ids}
    response = await client.post(
        f"/api/{version}/items/{item_id}/audios/",
        json=payload
    )
    assert response.status_code == status.HTTP_202_ACCEPTED

    read_audio_blocks_ids = [
        _id for _id, read in block_dict.items()
        if (read is True) and (_id in audio_blocks_ids)
    ]
    request.config.cache.set("read_audio_blocks_ids", read_audio_blocks_ids)


@pytest.mark.dependency(depends=["request_block_batch_audio"])
async def test_list_item_block_audios(
    version: str,
    client: AsyncClient,
    request
):
    item_id = request.config.cache.get("item_id", None)
    response = await client.get(f"/api/{version}/items/{item_id}/audios/")
    assert response.status_code == status.HTTP_200_OK
    blocks = response.json()
    read_audio_blocks_ids = request.config.cache.get("read_audio_blocks_ids", None)
    for block in blocks:
        if block["_id"] in read_audio_blocks_ids:
            assert block['audio_status'] == AudioStatus.COMPLETED
        else:
            assert 'audio_status' not in block
