import asyncio
import json
import httpx
from app.core.config import settings
from app.repositories.notify_rooms import get_by_id as get_notify_room_by_id

def resolve_notify_credentials(db=None, notify_room_id=None):
    base_url = (settings.moph_notify_base_url or "").rstrip("/")
    send_path = (settings.moph_notify_send_path or "/api/notify/send").strip()
    send_path = "/" + send_path.lstrip("/")
    client_key = settings.moph_notify_client_key or ""
    secret_key = settings.moph_notify_secret_key or ""
    room = None

    if db is not None and notify_room_id:
        try:
            room = get_notify_room_by_id(db, int(notify_room_id))
        except Exception:
            room = None
        if room:
            client_key = room.client_key or ""
            secret_key = room.secret_key or ""

    return {
        "base_url": base_url,
        "send_path": send_path,
        "client_key": client_key,
        "secret_key": secret_key,
        "room_name": getattr(room, "name", None),
        "room_id": getattr(room, "id", None),
    }

def _sanitize(base_url, send_path, client_key, secret_key):
    return {
        "base_url": base_url,
        "send_path": send_path,
        "normalized_url": f"{base_url}{send_path}",
        "client_key_present": bool(client_key),
        "secret_key_present": bool(secret_key),
    }

def normalize_result(payload):
    if not isinstance(payload, dict):
        return {"ok": False, "raw": payload, "data": None}
    data = payload.get("data", payload)
    ok = payload.get("status") in (200, "200", True) or data is not None
    return {"ok": ok, "raw": payload, "data": data}

async def health_check(db=None, notify_room_id=None):
    creds = resolve_notify_credentials(db=db, notify_room_id=notify_room_id)
    return {"status": "configured", **_sanitize(creds["base_url"], creds["send_path"], creds["client_key"], creds["secret_key"])}

async def send_messages(messages, db=None, notify_room_id=None, retries=3):
    creds = resolve_notify_credentials(db=db, notify_room_id=notify_room_id)
    url = f'{creds["base_url"]}{creds["send_path"]}'
    headers = {
        "Content-Type": "application/json",
        "client-key": creds["client_key"],
        "secret-key": creds["secret_key"],
    }
    body = {"messages": messages}
    last_exc = None

    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.post(url, json=body, headers=headers)
                text_body = response.text
                if response.status_code >= 400:
                    raise ValueError(json.dumps({
                        "http_status": response.status_code,
                        "response_text": text_body[:2000],
                        **_sanitize(creds["base_url"], creds["send_path"], creds["client_key"], creds["secret_key"]),
                    }, ensure_ascii=False))
                payload = response.json()
                result = normalize_result(payload)
                result["attempt"] = attempt
                result["room_name"] = creds["room_name"]
                result["room_id"] = creds["room_id"]
                return result
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                await asyncio.sleep(min(attempt, 3))
    raise last_exc

async def send_message(message, db=None, notify_room_id=None, retries=3):
    return await send_messages([message], db=db, notify_room_id=notify_room_id, retries=retries)
