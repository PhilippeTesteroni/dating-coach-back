from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for Dating Coach API"""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8007
    
    # Database
    database_url: str = "postgresql+asyncpg://localhost/shitty_apps"
    
    # AWS S3
    s3_bucket: str = "shittyapps-media"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    
    # Microservices URLs
    identity_service_url: str = "http://localhost:8001"
    config_service_url: str = "http://localhost:8002"
    payment_service_url: str = "http://localhost:8003"
    moderation_service_url: str = "http://localhost:8004"
    ai_gateway_url: str = "http://localhost:8005"
    
    # App Configuration
    app_id: str = "dating_coach"
    
    # Environment
    environment: str = "development"
    
    # JWT Settings (must match Identity Service!)
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()
