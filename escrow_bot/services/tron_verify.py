from __future__ import annotations

from dataclasses import dataclass

import httpx

USDT_TRC20_CONTRACT = "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"


@dataclass(frozen=True)
class TronTx:
    tx_hash: str
    to_addr: str
    contract: str
    amount_base_units: int
    confirmations: int
    success: bool


def parse_tron_tx(data: dict) -> TronTx:
    return TronTx(
        tx_hash=data["tx_hash"],
        to_addr=data["to"],
        contract=data["contract"],
        amount_base_units=int(data["amount_base_units"]),
        confirmations=int(data["confirmations"]),
        success=bool(data["success"]),
    )


def verify_tron_tx(
    tx_hash: str,
    expected_to: str,
    expected_amount: int,
    confirmations_required: int,
    api_url: str,
    expected_contract: str = USDT_TRC20_CONTRACT,
) -> TronTx:
    response = httpx.get(f"{api_url}/{tx_hash}", timeout=10.0)
    response.raise_for_status()
    tx = parse_tron_tx(response.json())
    if not tx.success:
        raise ValueError("Transaction not successful")
    if tx.contract != expected_contract:
        raise ValueError("Unexpected token contract")
    if tx.to_addr != expected_to:
        raise ValueError("Receiver mismatch")
    if tx.amount_base_units != expected_amount:
        raise ValueError("Amount mismatch")
    if tx.confirmations < confirmations_required:
        raise ValueError("Insufficient confirmations")
    return tx
