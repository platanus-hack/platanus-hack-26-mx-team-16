import boto3

from src.common.settings import settings


def get_s3_client():
    kwargs = {
        "endpoint_url": settings.AWS_S3_ENDPOINT_URL,
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "region_name": settings.AWS_S3_REGION_NAME,
    }
    if settings.AWS_SESSION_TOKEN is not None:
        kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN
    return boto3.client("s3", **kwargs)
