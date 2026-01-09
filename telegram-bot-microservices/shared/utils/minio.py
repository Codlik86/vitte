"""
MinIO/S3 client utility (optional - for file storage)
"""
import os
from typing import Optional
from minio import Minio
from minio.error import S3Error


class MinIOClient:
    """MinIO/S3 client wrapper"""
    
    def __init__(self):
        self.client: Optional[Minio] = None
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "vitte-bot")
        self.enabled = os.getenv("S3_ENABLED", "False").lower() == "true"
        
        if self.enabled:
            endpoint = os.getenv("S3_ENDPOINT", "minio:9000").replace("http://", "").replace("https://", "")
            access_key = os.getenv("S3_ACCESS_KEY", "minioadmin")
            secret_key = os.getenv("S3_SECRET_KEY", "minioadmin")
            
            self.client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False  # Use True for HTTPS
            )
            
            # Ensure bucket exists
            self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Create bucket if it doesn't exist"""
        if not self.client:
            return
            
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"Error ensuring bucket exists: {e}")
    
    def upload_file(self, file_path: str, object_name: str) -> str:
        """
        Upload file to MinIO
        
        Args:
            file_path: Local file path
            object_name: Object name in bucket
        
        Returns:
            URL to uploaded file
        """
        if not self.enabled or not self.client:
            return ""
        
        try:
            self.client.fput_object(
                self.bucket_name,
                object_name,
                file_path
            )
            
            # Return presigned URL (valid for 7 days)
            return self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=60 * 60 * 24 * 7
            )
        except S3Error as e:
            print(f"Error uploading file: {e}")
            return ""
    
    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """Get presigned URL for file"""
        if not self.enabled or not self.client:
            return ""
        
        try:
            return self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=expires
            )
        except S3Error as e:
            print(f"Error getting file URL: {e}")
            return ""


# Global MinIO client instance
minio_client = MinIOClient()
