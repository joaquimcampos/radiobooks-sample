
import os
from functools import cache
from io import BytesIO

import aioboto3
import boto3
import boto3.s3.transfer as s3transfer
import botocore
from s3transfer.futures import TransferFuture

from app.config.logging import LoggerValueError, get_logger
from app.config.settings import get_settings
from app.config.variables import AWS as VarConfig

logger = get_logger(__name__)

S3_WORKDIR: str = ""


def set_s3_workdir(prefix: str) -> None:
    global S3_WORKDIR
    S3_WORKDIR = prefix


def prepend_s3_workdir(s3_key: str) -> str:
    workdir = S3_WORKDIR
    full_s3_key = os.path.join(workdir, s3_key)
    if not full_s3_key:
        raise LoggerValueError(logger, 'Both workdir and s3_key are not set.')

    return full_s3_key


class S3Client:
    def __init__(self):
        self.num_workers = VarConfig.NUM_WORKERS
        botocore_config = botocore.config.Config(max_pool_connections=self.num_workers)
        settings = get_settings()
        assert not settings.LOCAL
        self.bucket = settings.AWS_S3_BUCKET
        self.session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME
        )
        self.client = self.session.client('s3', config=botocore_config)

    def write_stream_to_s3(self, contents: bytes, s3_key: str) -> None:
        temp_file = BytesIO()
        temp_file.write(contents)
        temp_file.seek(0)
        full_path = prepend_s3_workdir(s3_key)
        self.client.upload_fileobj(
            temp_file,
            self.bucket,
            full_path
        )
        temp_file.close()

    def write_file_to_s3(self, filename: str, s3_key: str) -> None:
        full_path = prepend_s3_workdir(s3_key)
        self.client.upload_file(
            filename, self.bucket, full_path
        )

    def delete_s3_obj(self, key: str) -> None:
        full_path = prepend_s3_workdir(key)
        self.client.delete_object(Bucket=self.bucket, Key=full_path)

    def delete_s3_objs_in_prefix(self, prefix: str) -> None:
        full_path = prepend_s3_workdir(prefix)
        response = self.client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=full_path
        )
        if response['KeyCount'] > 0:
            for object in response['Contents']:
                self.client.delete_object(Bucket=self.bucket, Key=object['Key'])


@cache
def get_s3_client() -> S3Client:
    return S3Client()


class S3Transfer:
    def __init__(self) -> None:
        s3_client = get_s3_client()
        self.bucket = get_settings().AWS_S3_BUCKET
        # The maximum number of concurrent S3 API transfer operations can be tuned to
        # adjust for the connection speed. Set the max_concurrency attribute to increase
        # or decrease bandwidth usage.
        # The attribute's default setting is 10. To reduce bandwidth usage, reduce the
        # value; to increase usage, increase it.
        transfer_config = s3transfer.TransferConfig(
            use_threads=True,
            max_concurrency=s3_client.num_workers,
        )
        # GB = 1024 ** 3
        # transfer_config = TransferConfig(multipart_threshold=5*GB)
        self.s3t = s3transfer.create_transfer_manager(
            s3_client.client, transfer_config
        )

    def get_s3_future(
        self,
        filename: str,
        s3_key: str
    ) -> TransferFuture:
        """
        https://stackoverflow.com/questions/56639630/
        how-can-i-increase-my-aws-s3-upload-speed-when-using-boto3
        """
        full_path = prepend_s3_workdir(s3_key)
        future = self.s3t.upload(filename, self.bucket, full_path)
        return future

    def shutdown(self):
        self.s3t.shutdown()


@cache
def get_s3_transfer() -> S3Transfer:
    return S3Transfer()


# Async version with aioboto3
class AsyncS3Session():
    def __init__(self):
        settings = get_settings()
        assert not settings.LOCAL
        self.bucket = settings.AWS_S3_BUCKET
        self.session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME
        )

    async def async_delete_objs_in_prefix(self, prefix: str) -> None:
        async with self.session.resource("s3") as s3:
            bucket = await s3.Bucket(self.bucket)
            full_path = prepend_s3_workdir(prefix)
            await bucket.objects.filter(Prefix=full_path).delete()


@cache
def get_async_s3_session() -> AsyncS3Session:
    return AsyncS3Session()
