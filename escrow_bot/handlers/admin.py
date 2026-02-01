from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from escrow_bot.config import load_config
from escrow_bot.ui.keyboards import admin_menu_keyboard
from escrow_bot.ui.render import render_admin_dashboard


def _is_admin(tg_id: int) -> bool:
    return tg_id in load_config().admin_ids


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return
    await update.message.reply_text(
        render_admin_dashboard(),
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu_keyboard(),
    )
