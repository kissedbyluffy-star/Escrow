from __future__ import annotations

import re

USERNAME_RE = re.compile(r"^@?[A-Za-z0-9_]{3,}$")
TX_HASH_RE = re.compile(r"^[a-fA-F0-9]{16,}$")


class ValidationError(ValueError):
    pass


def validate_username(username: str) -> str:
    if not USERNAME_RE.match(username):
        raise ValidationError("Invalid username")
    return username if username.startswith("@") else f"@{username}"


def validate_terms(terms: str) -> str:
    cleaned = terms.strip()
    if len(cleaned) < 40:
        raise ValidationError("Terms too short")
    required_keywords = ["deliver", "payment", "proof"]
    if not all(keyword in cleaned.lower() for keyword in required_keywords):
        raise ValidationError("Terms must define delivery, payment, and proof")
    return cleaned


def parse_amount(value: str, max_amount: int) -> int:
    try:
        amount = float(value)
    except ValueError as exc:
        raise ValidationError("Invalid amount") from exc
    if amount <= 0:
        raise ValidationError("Amount must be positive")
    base_units = int(amount * 1_000_000)
    if base_units > max_amount:
        raise ValidationError("Amount exceeds maximum")
    return base_units


def validate_tx_hash(tx_hash: str) -> str:
    if not TX_HASH_RE.match(tx_hash):
        raise ValidationError("Invalid transaction hash")
    return tx_hash
