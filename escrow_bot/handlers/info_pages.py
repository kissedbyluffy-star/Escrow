from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from escrow_bot.services.settings import get_setting
from escrow_bot.ui.keyboards import back_menu_keyboard
from escrow_bot.ui.render import (
    render_deposit_instructions,
    render_fees,
    render_how_it_works,
    render_terms,
)
from escrow_bot.ui import text


async def info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query:
        return
    data = update.callback_query.data
    await update.callback_query.answer()
    if data == "info:deposit":
        body = f"{text.DEPOSIT_HELP_TITLE}\n\n{text.DEPOSIT_HELP_BODY}"
    elif data == "info:fees":
        body = render_fees(get_setting("fee_percent"), get_setting("fee_flat"))
    elif data == "info:how":
        body = render_how_it_works()
    elif data == "info:terms":
        body = render_terms(get_setting("terms_version"))
    elif data == "info:updates":
        body = "<b>📢 Updates</b>"
    elif data == "info:vouches":
        body = "<b>✅ Vouches</b>"
    elif data == "info:support":
        body = "<b>🆘 Support</b>"
    else:
        body = "<b>Info</b>"
    await update.callback_query.message.reply_text(
        body, parse_mode=ParseMode.HTML, reply_markup=back_menu_keyboard()
    )


def build_deposit_help_message(deal: dict, address: str, memo: str | None) -> str:
    return render_deposit_instructions(deal, address, memo)
