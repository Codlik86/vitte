"""
Storage module for uploading generated images to MinIO
"""
import hashlib
import os
from datetime import datetime
from typing import Optional
from io import BytesIO

from minio import Minio
from minio.error import S3Error
from shared.utils import get_logger

logger = get_logger(__name__)

# MinIO configuration from environment
MINIO_ENDPOINT = os.getenv("S3_ENDPOINT", "minio:9000").replace("http://", "").replace("https://", "")
MINIO_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("S3_BUCKET_NAME", "vitte-bot")
MINIO_SECURE = os.getenv("S3_SECURE", "False").lower() == "true"

# Public URL base (через nginx)
PUBLIC_URL_BASE = os.getenv("PUBLIC_STORAGE_URL", "https://craveme.tech/storage")


def get_minio_client() -> Minio:
    """Get MinIO client instance."""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )


async def upload_generated_image(persona_key: str, image_data: bytes) -> Optional[str]:
    """
    Upload generated image to MinIO and return public URL.

    Args:
        persona_key: Persona identifier (lina, julie, etc.)
        image_data: Raw image bytes (PNG)

    Returns:
        Public URL if successful, None otherwise
    """
    try:
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        content_hash = hashlib.md5(image_data).hexdigest()[:8]
        filename = f"generated/{persona_key}/{timestamp}_{content_hash}.png"

        # Upload to MinIO
        client = get_minio_client()

        # Ensure bucket exists
        if not client.bucket_exists(MINIO_BUCKET):
            logger.warning(f"Bucket {MINIO_BUCKET} does not exist, creating...")
            client.make_bucket(MINIO_BUCKET)

        # Upload file
        client.put_object(
            MINIO_BUCKET,
            filename,
            BytesIO(image_data),
            length=len(image_data),
            content_type="image/png"
        )

        # Generate public URL
        public_url = f"{PUBLIC_URL_BASE}/{filename}"

        logger.info(f"Uploaded image to MinIO: {filename}, size={len(image_data)} bytes")
        return public_url

    except S3Error as e:
        logger.error(f"MinIO S3 error: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Failed to upload image to MinIO: {e}", exc_info=True)
        return None
