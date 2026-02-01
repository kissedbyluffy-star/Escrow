from __future__ import annotations

import hmac
import json
import time
from hashlib import sha256


class CallbackSignatureError(ValueError):
    pass


def sign_payload(payload: dict, secret: str, ttl_sec: int) -> str:
    payload_with_exp = payload.copy()
    payload_with_exp["exp"] = int(time.time()) + ttl_sec
    body = json.dumps(payload_with_exp, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(secret.encode(), body.encode(), sha256).hexdigest()
    return f"{body}.{signature}"


def verify_payload(token: str, secret: str) -> dict:
    try:
        body, signature = token.rsplit(".", 1)
    except ValueError as exc:
        raise CallbackSignatureError("Malformed token") from exc
    expected = hmac.new(secret.encode(), body.encode(), sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise CallbackSignatureError("Signature mismatch")
    payload = json.loads(body)
    if payload.get("exp", 0) <= int(time.time()):
        raise CallbackSignatureError("Token expired")
    return payload
