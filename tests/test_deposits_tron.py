import httpx
import pytest

from escrow_bot.services.tron_verify import USDT_TRC20_CONTRACT, verify_tron_tx


def _transport(data: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=data)

    return httpx.MockTransport(handler)


def test_tron_verify_success(monkeypatch: pytest.MonkeyPatch):
    data = {
        "tx_hash": "abcd1234abcd1234",
        "to": "TDEST",
        "contract": USDT_TRC20_CONTRACT,
        "amount_base_units": 1000,
        "confirmations": 25,
        "success": True,
    }
    transport = _transport(data)
    client = httpx.Client(transport=transport)
    monkeypatch.setattr(httpx, "get", client.get)
    tx = verify_tron_tx(
        "abcd1234abcd1234",
        expected_to="TDEST",
        expected_amount=1000,
        confirmations_required=20,
        api_url="https://tron.api",
    )
    assert tx.tx_hash == "abcd1234abcd1234"


def test_tron_verify_contract_mismatch(monkeypatch: pytest.MonkeyPatch):
    data = {
        "tx_hash": "abcd1234abcd1234",
        "to": "TDEST",
        "contract": "BAD",
        "amount_base_units": 1000,
        "confirmations": 25,
        "success": True,
    }
    transport = _transport(data)
    client = httpx.Client(transport=transport)
    monkeypatch.setattr(httpx, "get", client.get)
    with pytest.raises(ValueError):
        verify_tron_tx(
            "abcd1234abcd1234",
            expected_to="TDEST",
            expected_amount=1000,
            confirmations_required=20,
            api_url="https://tron.api",
        )
