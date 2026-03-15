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

def _extract_data(payload):
    if not isinstance(payload, dict):
        return {}
    return payload.get("data", payload)

def _pick_token(payload:dict):
    data = _extract_data(payload)
    return data.get("access_token") or data.get("token") or payload.get("access_token") or payload.get("token")

async def exchange_health_token(code: str) -> dict:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
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
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.post(
            settings.provider_service_token_url,
            json={
                "client_id": settings.provider_client_id,
                "secret_key": settings.provider_secret_key,
                "token_by": "Health ID",
                "token": health_access_token,
            },
            headers={"Content-Type": "application/json"},
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

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
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

async def test_provider_config() -> dict:
    checks = {
        "provider_login_enabled": settings.provider_login_enabled,
        "health_id_base_url": bool(settings.health_id_base_url),
        "health_id_client_id": bool(settings.health_id_client_id),
        "health_id_client_secret": bool(settings.health_id_client_secret),
        "health_id_redirect_uri": bool(settings.health_id_redirect_uri),
        "provider_client_id": bool(settings.provider_client_id),
        "provider_secret_key": bool(settings.provider_secret_key),
        "provider_service_token_url": bool(settings.provider_service_token_url),
        "provider_profile_url": bool(settings.provider_profile_url),
    }
    ok = all(checks.values())
    return {"status": "ok" if ok else "incomplete", "checks": checks}

async def exchange_profile(code: str) -> dict:
    if not settings.provider_login_enabled:
        return {
            "account_id": f"acc-{code}",
            "provider_id": f"provider-{code}",
            "username": f"provider-{code}",
            "display_name": "Provider Demo User",
        }

    health_payload = await exchange_health_token(code)
    health_access_token = _pick_token(health_payload)
    if not health_access_token:
        raise ValueError(f"Health ID access_token not found: {health_payload}")

    provider_token_payload = await exchange_provider_token(health_access_token)
    provider_access_token = _pick_token(provider_token_payload)
    if not provider_access_token:
        raise ValueError(f"Provider access_token not found: {provider_token_payload}")

    profile = await fetch_provider_profile(provider_access_token)
    if not isinstance(profile, dict) or not profile:
        raise ValueError("Provider profile response is empty")
    profile["_health_token_payload"] = _extract_data(health_payload)
    profile["_provider_token_payload"] = _extract_data(provider_token_payload)
    return profile
