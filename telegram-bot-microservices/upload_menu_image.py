"""
Upload universal menu image to MinIO

Run this script once to upload the menu image to MinIO storage.
"""
import os
import sys
from minio import Minio
from minio.error import S3Error

# MinIO configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
BUCKET_NAME = "vitte-bot"
IMAGE_PATH = "../universal_pic_square.jpeg"
OBJECT_NAME = "menu/universal_pic_square.jpeg"


def upload_image():
    """Upload menu image to MinIO"""
    try:
        # Initialize MinIO client
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )

        # Create bucket if doesn't exist
        if not client.bucket_exists(BUCKET_NAME):
            client.make_bucket(BUCKET_NAME)
            print(f"✓ Created bucket: {BUCKET_NAME}")
        else:
            print(f"✓ Bucket exists: {BUCKET_NAME}")

        # Upload image
        if not os.path.exists(IMAGE_PATH):
            print(f"✗ Image not found: {IMAGE_PATH}")
            return False

        client.fput_object(
            BUCKET_NAME,
            OBJECT_NAME,
            IMAGE_PATH,
            content_type="image/jpeg"
        )

        print(f"✓ Uploaded: {OBJECT_NAME}")

        # Make object publicly accessible (optional)
        # For now we'll use presigned URLs in the bot

        # Get presigned URL (7 days)
        url = client.presigned_get_object(
            BUCKET_NAME,
            OBJECT_NAME,
            expires=60 * 60 * 24 * 7
        )
        print(f"✓ Image URL (7 days): {url[:80]}...")

        return True

    except S3Error as e:
        print(f"✗ MinIO error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    print("Uploading menu image to MinIO...")
    success = upload_image()
    sys.exit(0 if success else 1)
