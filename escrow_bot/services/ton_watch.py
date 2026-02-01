from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import httpx


@dataclass(frozen=True)
class TonTx:
    tx_hash: str
    to_addr: str
    memo: str
    amount_base_units: int
    confirmations: int
    success: bool


def parse_ton_transactions(data: dict) -> Iterable[TonTx]:
    for item in data.get("transactions", []):
        yield TonTx(
            tx_hash=item["hash"],
            to_addr=item["to"],
            memo=item.get("memo", ""),
            amount_base_units=int(item["amount_base_units"]),
            confirmations=int(item["confirmations"]),
            success=bool(item.get("success", True)),
        )


def find_matching_deposit(
    txs: Iterable[TonTx],
    expected_addr: str,
    expected_memo: str,
    expected_amount: int,
    confirmations_required: int,
) -> TonTx | None:
    for tx in txs:
        if not tx.success:
            continue
        if tx.to_addr != expected_addr:
            continue
        if tx.memo != expected_memo:
            continue
        if tx.amount_base_units != expected_amount:
            continue
        if tx.confirmations < confirmations_required:
            continue
        return tx
    return None


def poll_ton_api(url: str) -> list[TonTx]:
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()
    return list(parse_ton_transactions(response.json()))
