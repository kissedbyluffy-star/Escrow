from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class DepositExpectation:
    address: str
    amount: float
    memo: str | None
    confirmations_required: int
    currency: str
    network: str


def format_ton_memo(deal_id: str) -> str:
    return f"DEAL-{deal_id}"


def ton_memo_matches(comment: str | None, expected_memo: str) -> bool:
    if not comment:
        return False
    return comment.strip() == expected_memo


def parse_ton_transactions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload.get("result", []) if isinstance(payload, dict) else []


def ton_tx_matches(tx: dict[str, Any], expectation: DepositExpectation) -> bool:
    if tx.get("to") != expectation.address:
        return False
    if expectation.memo and not ton_memo_matches(tx.get("message"), expectation.memo):
        return False
    value = float(tx.get("value", 0)) / 1e9
    if round(value, 8) != round(expectation.amount, 8):
        return False
    confirmations = int(tx.get("confirmations", 0))
    return confirmations >= expectation.confirmations_required


def tron_usdt_matches(tx: dict[str, Any], expectation: DepositExpectation) -> tuple[bool, str]:
    if tx.get("contract_type") != "TRC20":
        return False, "Not a TRC20 transfer."
    token = tx.get("token_info", {})
    if token.get("symbol") != "USDT":
        return False, "Token is not USDT."
    to_address = tx.get("to_address")
    if to_address != expectation.address:
        return False, "Receiver address mismatch."
    amount = float(tx.get("amount", 0)) / 1e6
    if round(amount, 8) != round(expectation.amount, 8):
        return False, "Amount mismatch."
    confirmations = int(tx.get("confirmations", 0))
    if confirmations < expectation.confirmations_required:
        return False, "Not enough confirmations yet."
    return True, ""


def extract_tron_tx_hash(tx: dict[str, Any]) -> str | None:
    return tx.get("hash") or tx.get("transaction_id")


def parse_tron_response(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("data") or payload


def _fetch_json(url: str, params: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    query = urlencode(params)
    request = Request(f"{url}?{query}", headers=headers or {})
    with urlopen(request, timeout=10) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


async def fetch_tron_transaction(tx_hash: str, api_url: str) -> dict[str, Any]:
    return await asyncio.to_thread(_fetch_json, api_url, {"hash": tx_hash}, None)


async def fetch_ton_transactions(address: str, api_url: str, limit: int = 10, api_key: str | None = None) -> dict[str, Any]:
    headers = {"X-API-Key": api_key} if api_key else None
    params = {"address": address, "limit": limit}
    return await asyncio.to_thread(_fetch_json, api_url, params, headers)
