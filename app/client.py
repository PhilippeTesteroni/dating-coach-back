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

    async def check_balance(
        self,
        jwt_token: str,
        welcome_bonus: int = None
    ) -> Dict[str, Any]:
        """
        Get user balance from Payment Service.
        
        Args:
            jwt_token: JWT access token (contains user_id)
            welcome_bonus: Bonus for new users (from Config Service)
        """
        url = f"{settings.payment_service_url}/v1/payment/balance"
        params = {}
        if welcome_bonus is not None:
            params["welcome_bonus"] = welcome_bonus
        
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        logger.info(f"🚀 [Payment] GET {url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"✅ [Payment] balance={data.get('balance')}")
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [Payment] HTTP {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ [Payment] Request failed: {e}")
            raise

    async def deduct_credits(
        self,
        jwt_token: str,
        amount: int,
        reason: str = "chat_message"
    ) -> Dict[str, Any]:
        """
        Deduct credits via Payment Service.
        
        Returns:
            {success: bool, new_balance: int} or {success: false, error: str}
        """
        url = f"{settings.payment_service_url}/v1/payment/deduct"
        headers = {"Authorization": f"Bearer {jwt_token}"}
        payload = {"amount": amount, "reason": reason}
        
        logger.info(f"🚀 [Payment] POST {url} amount={amount}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ [Payment] deduct success={data.get('success')}, new_balance={data.get('new_balance')}")
            return data

    async def get_app_settings(self) -> Dict[str, Any]:
        """Get app settings from Config Service"""
        url = f"{settings.config_service_url}/v1/config/app-settings"
        params = {"app_id": settings.app_id}
        
        logger.info(f"🚀 [Config] GET {url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"✅ [Config] settings loaded")
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [Config] HTTP {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ [Config] Request failed: {e}")
            raise

    async def verify_purchase(
        self,
        jwt_token: str,
        product_id: str,
        purchase_token: str,
        platform: str = "google_play"
    ) -> Dict[str, Any]:
        """
        Verify purchase via Payment Service.
        
        Args:
            jwt_token: JWT access token (contains user_id)
            product_id: Google Play product ID (e.g. credits_10)
            purchase_token: Google Play purchase token
            platform: Platform identifier
            
        Returns:
            {success: bool, credits_added: int, new_balance: int}
        """
        url = f"{settings.payment_service_url}/v1/payment/verify-purchase"
        headers = {"Authorization": f"Bearer {jwt_token}"}
        payload = {
            "product_id": product_id,
            "purchase_token": purchase_token,
            "platform": platform
        }
        
        logger.info(f"🚀 [Payment] POST {url}")
        logger.info(f"📦 [Payment] product={product_id}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"✅ [Payment] credits_added={data.get('credits_added')}, new_balance={data.get('new_balance')}")
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [Payment] HTTP {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ [Payment] Request failed: {e}")
            raise


    async def get_characters(self) -> Dict[str, Any]:
        """
        Get characters config from Config Service.
        
        Returns:
            {version: str, characters: list}
        """
        url = f"{settings.config_service_url}/v1/config/characters"
        params = {"app_id": settings.app_id}
        
        logger.info(f"🚀 [Config] GET {url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"✅ [Config] characters loaded, count={len(data.get('characters', []))}")
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [Config] HTTP {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ [Config] Request failed: {e}")
            raise

    async def get_file(self, path: str) -> Dict[str, Any]:
        """
        Get any allowed file from Config Service.
        
        Args:
            path: File path within app folder (e.g., "templates/character_system.txt")
            
        Returns:
            {path: str, content_type: str, content: str|dict}
        """
        url = f"{settings.config_service_url}/v1/config/file"
        params = {"app_id": settings.app_id, "path": path}
        
        logger.info(f"🚀 [Config] GET {url} path={path}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"✅ [Config] file loaded: {path}")
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [Config] HTTP {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ [Config] Request failed: {e}")
            raise

    async def get_modes(self) -> Dict[str, Any]:
        """
        Get modes config from Config Service.
        
        Returns:
            {version: str, categories: list, modes: list}
        """
        data = await self.get_file("modes.json")
        return data.get("content", {})

    async def get_template(self, name: str) -> str:
        """
        Get template file content.
        
        Args:
            name: Template name without extension (e.g., "character_system")
            
        Returns:
            Template content as string
        """
        data = await self.get_file(f"templates/{name}.txt")
        return data.get("content", "")

    async def get_scenario(self, mode_id: str) -> Dict[str, Any]:
        """
        Get scenario config for a mode.
        
        Args:
            mode_id: Mode identifier (e.g., "open_chat")
            
        Returns:
            {mode_id: str, scenario_prompt: str, difficulty_levels: list|null}
        """
        data = await self.get_file(f"scenarios/{mode_id}.json")
        return data.get("content", {})

    async def call_ai(
        self,
        messages: list,
        system_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.8
    ) -> str:
        """
        Call AI Gateway for chat completion.
        
        Args:
            messages: List of {role, content} dicts
            system_prompt: System prompt for AI
            max_tokens: Max response tokens
            temperature: Sampling temperature
            
        Returns:
            AI response text
        """
        url = f"{settings.ai_gateway_url}/v1/ai/chat"
        payload = {
            "app_id": settings.app_id,
            "messages": messages,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        logger.info(f"🚀 [AI Gateway] POST {url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.ai_timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                content = data.get("content", "")
                logger.info(f"✅ [AI Gateway] response received, len={len(content)}")
                return content
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [AI Gateway] HTTP {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ [AI Gateway] Request failed: {e}")
            raise


# Global instance
service_client = ServiceClient()
