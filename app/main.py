from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware

from app.config.database import async_init_databases
from app.config.logging import get_logger
from app.config.settings import get_settings
from app.config.variables import Routers as VarConfig  # type: ignore
from app.models.responses import ShortResponse
from app.routers import router as v1
from app.routers.health import router as health_router

if get_settings().LOCAL:
    get_logger("uvicorn")

app = FastAPI(
    title="Radiobooks API",
    version=get_settings().APP_VERSION,
)


origins = [
    # NOTE: Other origins are ommited
    "http://localhost:8080",
]

# Middlewares: order of in requests: last to first, order of responses: first to last.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.middleware("http")
async def set_content_encoding_to_none(request: Request, call_next):
    """https://community.fly.io/t/content-encoding-gzip/4000/30"""
    response = await call_next(request)
    response.headers["Content-Encoding"] = "none"
    if "Content-Length" not in response.headers:
        response.headers["Content-Length"] = response.headers[
            VarConfig.FULL_CONTENT_LENGTH_HEADER
        ]
    # delete X-Full-Content-Length header
    del response.headers[VarConfig.FULL_CONTENT_LENGTH_HEADER]

    return response


app.include_router(v1, prefix="/api/v1")
app.include_router(health_router, prefix="/health", tags=["health"])


@app.on_event("startup")
async def startup_event():
    app.state.logger = get_logger(__name__)
    app.state.logger.info("Server starting...")
    await async_init_databases(app.state)


@app.get(
    "/",
    tags=["root"],
    status_code=status.HTTP_200_OK,
    response_description=("Show welcoming message."),
    response_model=ShortResponse
)
async def read_root():
    return ShortResponse(message="Welcome to the Radiobooks API.")


@app.get(
    "/aws_root_path",
    tags=["aws"],
    status_code=status.HTTP_200_OK,
    response_description=("Show welcoming message."),
    response_model=ShortResponse
)
async def get_aws_root_path():
    return ShortResponse(
        message=(
            "https://{}.s3.{}.amazonaws.com"
            .format(get_settings().AWS_S3_BUCKET, get_settings().AWS_REGION_NAME)
        )
    )


@app.on_event("shutdown")
async def shutdown_event():
    app.state.logger.info("Server stopping.")
