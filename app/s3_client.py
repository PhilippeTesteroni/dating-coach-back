import boto3
from botocore.config import Config
from uuid import UUID

from app.config import settings


class S3Client:
    """S3 client for avatar uploads"""
    
    def __init__(self):
        self.bucket = settings.s3_bucket
        self.region = settings.aws_region
        
        # Initialize boto3 client
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            self.client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                config=Config(signature_version='s3v4')
            )
        else:
            # Use IAM role
            self.client = boto3.client(
                's3',
                region_name=self.region,
                config=Config(signature_version='s3v4')
            )
    
    def get_avatar_key(self, user_id: UUID) -> str:
        """Generate S3 key for user avatar"""
        return f"avatars/dating_coach/{user_id}.jpg"
    
    def get_avatar_url(self, user_id: UUID) -> str:
        """Get public URL for avatar"""
        key = self.get_avatar_key(user_id)
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
    
    def generate_presigned_upload_url(
        self, 
        user_id: UUID, 
        expires_in: int = 300
    ) -> str:
        """
        Generate presigned URL for direct upload to S3.
        
        Args:
            user_id: User's UUID
            expires_in: URL expiration in seconds (default 5 min)
        
        Returns:
            Presigned URL for PUT request
        """
        key = self.get_avatar_key(user_id)
        
        url = self.client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': self.bucket,
                'Key': key,
                'ContentType': 'image/jpeg',
            },
            ExpiresIn=expires_in
        )
        
        return url


# Global instance
s3_client = S3Client()
