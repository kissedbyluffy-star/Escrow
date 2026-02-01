from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from escrow_bot.ui.keyboards import back_menu_keyboard


async def deals_placeholder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "<b>Deals</b>\n\nDeal flows are initiated via buttons.",
        parse_mode=ParseMode.HTML,
        reply_markup=back_menu_keyboard(),
    )
