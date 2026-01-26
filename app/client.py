import httpx
import logging
from typing import Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


class ServiceClient:
    """Client for communicating with platform microservices"""
    
    def __init__(self):
        self.timeout = httpx.Timeout(30.0)
        self.ai_timeout = httpx.Timeout(90.0)
    
    async def get_auth_token(
        self, 
        device_id: str, 
        platform: str = "android"
    ) -> Dict[str, Any]:
        """
        Get JWT tokens from Identity Service.
        
        Maps device_id to internal user_id and returns tokens.
        Creates new user if device_id is not found.
        """
        url = f"{settings.identity_service_url}/v1/auth/token"
        payload = {
            "platform": platform,
            "external_id": device_id,
            "metadata": {
                "app_id": settings.app_id
            }
        }
        
        logger.info(f"🚀 [Identity] POST {url}")
        logger.info(f"📦 [Identity] platform={platform}, device_id={device_id[:8]}...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"✅ [Identity] user_id={data.get('user_id')}")
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [Identity] HTTP {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ [Identity] Request failed: {e}")
            raise
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        url = f"{settings.identity_service_url}/v1/auth/refresh"
        payload = {"refresh_token": refresh_token}
        
        logger.info(f"🚀 [Identity] POST {url} (refresh)")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [Identity] Refresh failed: {e.response.status_code}")
            raise
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token via Identity Service"""
        url = f"{settings.identity_service_url}/v1/auth/validate"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json={"token": token})
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError:
            return None


# Global instance
service_client = ServiceClient()
