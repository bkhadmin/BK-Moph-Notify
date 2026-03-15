import asyncio, httpx
from app.core.config import settings

def normalize_result(payload:dict) -> dict:
    if not isinstance(payload, dict):
        return {"raw": payload, "ok": False}
    data = payload.get("data", payload)
    return {"ok": payload.get("status") in (200, "200", True) or data is not None, "data": data, "raw": payload}

async def send_messages(messages: list[dict], retries:int=3) -> dict:
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.moph_notify_base_url}{settings.moph_notify_send_path}",
                    json={"messages": messages},
                    headers={
                        "Content-Type": "application/json",
                        "client-key": settings.moph_notify_client_key,
                        "secret-key": settings.moph_notify_secret_key,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                result = normalize_result(payload)
                result["attempt"] = attempt
                return result
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                await asyncio.sleep(min(attempt, 3))
    raise last_exc
