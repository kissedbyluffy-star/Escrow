from __future__ import annotations

import re

USERNAME_RE = re.compile(r"@([A-Za-z0-9_]{3,})")
TX_RE = re.compile(r"\b([a-fA-F0-9]{8,})\b")


def mask_username(username: str, mode: str = "masked") -> str:
    if len(username) <= 4:
        return username[0] + "***"
    if mode == "extra-masked":
        return f"{username[0]}***"
    return f"{username[:2]}***{username[-2:]}"


def mask_tx(tx_hash: str, mode: str = "masked") -> str:
    if len(tx_hash) <= 8:
        return tx_hash
    if mode == "extra-masked":
        return f"{tx_hash[:4]}..."
    return f"{tx_hash[:4]}...{tx_hash[-4:]}"


def mask_text(text: str, mode: str = "masked") -> str:
    def _mask_user(match: re.Match[str]) -> str:
        return "@" + mask_username(match.group(1), mode)

    def _mask_tx(match: re.Match[str]) -> str:
        return mask_tx(match.group(1), mode)

    text = USERNAME_RE.sub(_mask_user, text)
    return TX_RE.sub(_mask_tx, text)
