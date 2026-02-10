import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def get_s3_client():
    """Create S3-compatible client for MinIO."""
    endpoint_url = f"http{'s' if settings.MINIO_USE_SSL else ''}://{settings.MINIO_ENDPOINT}:{settings.MINIO_PORT}"
    
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD.get_secret_value(),
        region_name=settings.MINIO_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket_exists():
    """Create bucket if it doesn't exist. Safe to call on every startup."""
    client = get_s3_client()
    bucket = settings.MINIO_BUCKET
    
    try:
        client.head_bucket(Bucket=bucket)
        logger.info(f"Bucket '{bucket}' already exists")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code in ("404", "NoSuchBucket"):
            try:
                client.create_bucket(Bucket=bucket)
                logger.info(f"Created bucket '{bucket}'")
            except ClientError as create_error:
                logger.error(f"Failed to create bucket '{bucket}': {create_error}")
                raise
        else:
            logger.error(f"Error checking bucket '{bucket}': {e}")
            raise


def put_object_bytes(key: str, data: bytes, content_type: str) -> None:
    """Upload bytes to MinIO."""
    client = get_s3_client()
    client.put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def get_presigned_get_url(key: str, expires_seconds: int = 3600) -> str:
    """Generate a presigned URL for downloading an object."""
    # Use external endpoint for presigned URLs
    external_endpoint = f"http{'s' if settings.MINIO_USE_SSL else ''}://{settings.MINIO_EXTERNAL_ENDPOINT}:{settings.MINIO_EXTERNAL_PORT}"
    
    external_client = boto3.client(
        "s3",
        endpoint_url=external_endpoint,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD.get_secret_value(),
        region_name=settings.MINIO_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    
    url = external_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.MINIO_BUCKET, "Key": key},
        ExpiresIn=expires_seconds,
    )
    return url


def delete_object(key: str) -> None:
    """Delete an object from MinIO."""
    client = get_s3_client()
    client.delete_object(Bucket=settings.MINIO_BUCKET, Key=key)


def delete_objects_by_prefix(prefix: str, ignore_not_found: bool = False) -> int:
    """Delete all objects with a given prefix. Returns count of deleted objects.
    If ignore_not_found=True, 404/NoSuchBucket is logged and 0 is returned (idempotent)."""
    client = get_s3_client()
    bucket = settings.MINIO_BUCKET
    deleted_count = 0

    try:
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        for page in pages:
            if "Contents" not in page:
                continue

            objects_to_delete = [{"Key": obj["Key"]} for obj in page["Contents"]]
            if objects_to_delete:
                try:
                    client.delete_objects(
                        Bucket=bucket,
                        Delete={"Objects": objects_to_delete}
                    )
                    deleted_count += len(objects_to_delete)
                except ClientError as e:
                    if ignore_not_found and e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NoSuchBucket"):
                        pass
                    else:
                        raise

        logger.info(f"Deleted {deleted_count} objects with prefix '{prefix}'")
        return deleted_count
    except ClientError as e:
        if ignore_not_found and e.response.get("Error", {}).get("Code") in ("404", "NoSuchBucket"):
            logger.info(f"No objects to delete for prefix '{prefix}' (bucket or prefix not found)")
            return 0
        logger.error(f"Failed to delete objects with prefix '{prefix}': {e}")
        raise


def list_objects_by_prefix(prefix: str) -> list:
    """List all objects with a given prefix. Returns list of keys."""
    client = get_s3_client()
    bucket = settings.MINIO_BUCKET
    keys = []
    
    try:
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        for page in pages:
            if "Contents" not in page:
                continue
            keys.extend([obj["Key"] for obj in page["Contents"]])
        
        return keys
    except ClientError as e:
        logger.error(f"Failed to list objects with prefix '{prefix}': {e}")
        return []


def get_object_bytes(key: str) -> bytes:
    """Download object bytes from MinIO."""
    client = get_s3_client()
    response = client.get_object(Bucket=settings.MINIO_BUCKET, Key=key)
    return response["Body"].read()

