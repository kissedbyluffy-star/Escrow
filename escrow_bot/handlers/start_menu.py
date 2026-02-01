from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from escrow_bot.services.db import db_session
from escrow_bot.services.settings import get_setting
from escrow_bot.ui.keyboards import menu_keyboard, terms_accept_keyboard
from escrow_bot.ui.render import render_home, render_terms


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_user(tg_id: int) -> None:
    with db_session() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (tg_id, first_seen_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (tg_id, _now(), _now(), _now()),
        )


def _has_accepted_terms(tg_id: int) -> bool:
    terms_version = get_setting("terms_version")
    require_reaccept = get_setting("REQUIRE_TERMS_REACCEPT_ON_UPDATE") == "1"
    with db_session() as conn:
        row = conn.execute(
            "SELECT terms_version FROM terms_acceptance WHERE tg_id = ?", (tg_id,)
        ).fetchone()
    if not row:
        return False
    if require_reaccept and row["terms_version"] != terms_version:
        return False
    return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    _ensure_user(update.effective_user.id)
    terms_version = get_setting("terms_version")
    if not _has_accepted_terms(update.effective_user.id):
        await update.message.reply_text(
            render_terms(terms_version),
            parse_mode=ParseMode.HTML,
            reply_markup=terms_accept_keyboard(),
        )
        return
    await update.message.reply_text(
        render_home(), parse_mode=ParseMode.HTML, reply_markup=menu_keyboard()
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    _ensure_user(update.effective_user.id)
    await update.message.reply_text(
        render_home(), parse_mode=ParseMode.HTML, reply_markup=menu_keyboard()
    )


async def terms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query or not update.effective_user:
        return
    data = update.callback_query.data
    if data == "terms:exit":
        await update.callback_query.answer("Terms required to use escrow.")
        return
    if data == "terms:accept":
        terms_version = get_setting("terms_version")
        with db_session() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO terms_acceptance (tg_id, terms_version, accepted_at) "
                "VALUES (?, ?, ?)",
                (update.effective_user.id, terms_version, _now()),
            )
        await update.callback_query.answer("Terms accepted.")
        await update.callback_query.message.reply_text(
            render_home(), parse_mode=ParseMode.HTML, reply_markup=menu_keyboard()
        )
