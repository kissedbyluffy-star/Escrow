import pytest

from escrow_bot.utils.state_machine import InvalidTransition, ensure_transition


def test_invalid_transition():
    with pytest.raises(InvalidTransition):
        ensure_transition("DRAFT", "FUNDED")
