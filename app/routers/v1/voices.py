import os

from fastapi import APIRouter, Path, status

from app.config.logging import get_exc_msg, get_logger
from app.config.variables import Voices as VarConfig  # type: ignore
from app.models.voices import Language, Voice  # type: ignore
from app.routers.http_exceptions import BadRequestHTTPException
from app.utils.aws import get_language_samples_prefix
from app.utils.voices import (  # type: ignore
    get_language_list, get_voice_list_for_language,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/languages",
    status_code=status.HTTP_200_OK,
    description="List the available languages.",
    response_description="A list of :Language: models",
    response_model=list[Language],
)
async def list_languages():
    lang_list = [
        Language(**language)
        for language in get_language_list(name_only=False)  # noqa: F821
        if language["name"] in VarConfig.SUPPORTED_LANGUAGES.keys()
    ]
    return lang_list


@router.get(
    "/languages/{name}/voices",
    status_code=status.HTTP_200_OK,
    description="List the available voices for a given language.",
    response_description="A list of :Voice: models",
    response_model=list[Voice],
    response_model_exclude_none=True,
    responses={
        status.HTTP_400_BAD_REQUEST: BadRequestHTTPException.response
    },
)
async def list_voices_for_language(
    name: str = Path(title="Language name")
):
    try:
        if name not in VarConfig.SUPPORTED_LANGUAGES.keys():
            raise ValueError(f'Language {name} is not supported.')

        voice_list: list[Voice] = []
        for voice in get_voice_list_for_language(  # noqa: F821
            name, name_only=False
        ):
            if (voice["name"] not in
                    VarConfig.SUPPORTED_LANGUAGES[name]["voices"]):
                continue

            voice["sample_audio_path"] = os.path.join(
                get_language_samples_prefix(name),
                f'{voice["name"]}.wav'
            )
            voice_list.append(Voice.parse_obj(voice))

    except ValueError as exc:
        raise BadRequestHTTPException(get_exc_msg(exc=exc))

    return voice_list
