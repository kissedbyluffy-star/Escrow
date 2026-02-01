from __future__ import annotations

ALLOWED_TRANSITIONS = {
    "DRAFT": {"CONFIRMED"},
    "CONFIRMED": {"FUNDED"},
    "FUNDED": {"DELIVERED", "DISPUTED"},
    "DELIVERED": {"READY_TO_PAYOUT", "DISPUTED"},
    "READY_TO_PAYOUT": {"RELEASED"},
    "RELEASED": {"CLOSED"},
    "DISPUTED": {"READY_TO_PAYOUT", "CLOSED"},
    "CLOSED": set(),
}


class InvalidTransition(ValueError):
    pass


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def ensure_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise InvalidTransition(f"Invalid transition {current} -> {target}")
