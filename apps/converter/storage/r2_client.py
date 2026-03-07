import boto3
import os
from botocore.exceptions import ClientError


def get_r2_client():
    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def get_bucket_name() -> str:
    return os.environ["R2_BUCKET_NAME"]


def download_from_r2(key: str, local_path: str) -> None:
    """Download a file from R2 to a local path."""
    client = get_r2_client()
    client.download_file(get_bucket_name(), key, local_path)


def upload_to_r2(local_path: str, key: str, content_type: str) -> None:
    """Upload a local file to R2."""
    client = get_r2_client()
    client.upload_file(
        local_path,
        get_bucket_name(),
        key,
        ExtraArgs={
            "ContentType": content_type,
            "Metadata": {"converted": "true"},
        },
    )
