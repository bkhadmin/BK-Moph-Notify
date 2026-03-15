import secrets
from urllib.parse import urlencode
import httpx
from app.core.config import settings

def provider_login_url() -> str:
    query = {
        "client_id": settings.health_id_client_id,
        "redirect_uri": settings.health_id_redirect_uri,
        "response_type": "code",
        "state": secrets.token_urlsafe(16),
    }
    return f"{settings.health_id_base_url}/oauth/redirect?{urlencode(query)}"

async def exchange_health_token(code: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.health_id_base_url}/api/v1/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.health_id_redirect_uri,
                "client_id": settings.health_id_client_id,
                "client_secret": settings.health_id_client_secret,
            },
        )
        response.raise_for_status()
        return response.json()

async def exchange_provider_token(health_access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            settings.provider_service_token_url,
            json={
                "client_id": settings.provider_client_id,
                "secret_key": settings.provider_secret_key,
                "token_by": "Health ID",
                "token": health_access_token,
            },
        )
        response.raise_for_status()
        return response.json()

async def fetch_provider_profile(provider_access_token: str) -> dict:
    params = {}
    if settings.provider_profile_moph_center_token in (0, 1):
        params["moph_center_token"] = str(settings.provider_profile_moph_center_token)
    if settings.provider_profile_moph_idp_permission in (0, 1):
        params["moph_idp_permission"] = str(settings.provider_profile_moph_idp_permission)
    if settings.provider_profile_position_type in (0, 1):
        params["position_type"] = str(settings.provider_profile_position_type)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            settings.provider_profile_url,
            params=params,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider_access_token}",
                "client-id": settings.provider_client_id,
                "secret-key": settings.provider_secret_key,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", payload) if isinstance(payload, dict) else {}

async def exchange_profile(code: str) -> dict:
    if not settings.provider_login_enabled:
        return {
            "account_id": f"acc-{code}",
            "provider_id": f"provider-{code}",
            "username": f"provider-{code}",
            "display_name": "Provider Demo User",
        }

    health_payload = await exchange_health_token(code)
    health_data = health_payload.get("data", health_payload)
    health_access_token = health_data.get("access_token")
    if not health_access_token:
        raise ValueError("Health ID access_token not found")

    provider_token_payload = await exchange_provider_token(health_access_token)
    provider_token_data = provider_token_payload.get("data", provider_token_payload)
    provider_access_token = provider_token_data.get("access_token")
    if not provider_access_token:
        raise ValueError("Provider access_token not found")

    profile = await fetch_provider_profile(provider_access_token)
    profile["_health_token_payload"] = health_data
    profile["_provider_token_payload"] = provider_token_data
    return profile
