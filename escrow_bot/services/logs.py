from __future__ import annotations

from escrow_bot.services.settings import get_setting
from escrow_bot.utils.masking import mask_text
from escrow_bot.ui.render import render_log_private, render_log_public


def format_private(message: str) -> str:
    return render_log_private(message)


def format_public(message: str) -> str:
    mode = get_setting("PUBLIC_MASK_MODE")
    masked = mask_text(message, mode=mode)
    return render_log_public(masked)
