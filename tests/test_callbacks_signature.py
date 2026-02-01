import time

import pytest

from escrow_bot.utils.security_callbacks import CallbackSignatureError, sign_payload, verify_payload


def test_callback_signature_roundtrip(monkeypatch: pytest.MonkeyPatch):
    token = sign_payload({"action": "release"}, secret="secret", ttl_sec=60)
    payload = verify_payload(token, secret="secret")
    assert payload["action"] == "release"


def test_callback_signature_expired(monkeypatch: pytest.MonkeyPatch):
    token = sign_payload({"action": "release"}, secret="secret", ttl_sec=1)
    time.sleep(1.1)
    with pytest.raises(CallbackSignatureError):
        verify_payload(token, secret="secret")
