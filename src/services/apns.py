import logging
import os
import time

import httpx
import jwt

logger = logging.getLogger(__name__)

_TEAM_ID = os.getenv("APNS_TEAM_ID", "F8DS796RUT")
_BUNDLE_ID = os.getenv("APNS_BUNDLE_ID", "me.mianfg.movgr")
_KEY_ID = os.getenv("APNS_KEY_ID")
_KEY_P8 = os.getenv("APNS_KEY_P8", "").replace("\\n", "\n")

_jwt: str | None = None
_jwt_iat = 0
_client: httpx.Client | None = None


def is_configured() -> bool:
    return bool(_KEY_ID and _KEY_P8)


def is_device_token(token: str) -> bool:
    value = token.strip().lower()
    return len(value) >= 64 and all(char in "0123456789abcdef" for char in value)


def _token() -> str | None:
    global _jwt, _jwt_iat
    if not is_configured():
        return None
    now = int(time.time())
    if _jwt and now - _jwt_iat < 50 * 60:
        return _jwt
    encoded = jwt.encode(
        {"iss": _TEAM_ID, "iat": now},
        _KEY_P8,
        algorithm="ES256",
        headers={"kid": _KEY_ID, "typ": "JWT"},
    )
    _jwt = encoded.decode() if isinstance(encoded, bytes) else encoded
    _jwt_iat = now
    return _jwt


def _http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(http2=True, timeout=12.0)
    return _client


def _host(environment: str) -> str:
    if environment == "sandbox":
        return "https://api.sandbox.push.apple.com"
    return "https://api.push.apple.com"


def send_live_update(
    device_token: str,
    environment: str,
    content_state: dict,
    stale_date: int,
    event: str = "update",
) -> int:
    auth = _token()
    if not auth or not is_device_token(device_token):
        return 400
    url = f"{_host(environment)}/3/device/{device_token}"
    headers = {
        "authorization": f"bearer {auth}",
        "apns-topic": f"{_BUNDLE_ID}.push-type.liveactivity",
        "apns-push-type": "liveactivity",
        "apns-priority": "10",
        "content-type": "application/json",
    }
    body = {
        "aps": {
            "timestamp": int(time.time()),
            "event": event,
            "content-state": content_state,
            "stale-date": stale_date,
            "relevance-score": 100,
        }
    }
    try:
        response = _http().post(url, json=body, headers=headers)
        if response.status_code >= 400:
            logger.warning("APNs %s: %s", response.status_code, response.text[:300])
        return response.status_code
    except Exception:
        logger.exception("APNs request failed")
        return 0
