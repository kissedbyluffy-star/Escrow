from __future__ import annotations

import argparse
import asyncio

from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from escrow_bot.config import load_config
from escrow_bot.handlers.admin import admin_panel
from escrow_bot.handlers.info_pages import info_callback
from escrow_bot.handlers.start_menu import menu_command, start_command, terms_callback
from escrow_bot.services.db import init_db
from escrow_bot.services.settings import seed_defaults


async def _startup_check() -> None:
    config = load_config()
    if not config.bot_token:
        raise SystemExit("BOT_TOKEN is required")


def build_application() -> tuple:
    config = load_config()
    application = ApplicationBuilder().token(config.bot_token).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(info_callback, pattern=r"^info:"))
    application.add_handler(CallbackQueryHandler(terms_callback, pattern=r"^terms:"))
    return application, config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    init_db()
    seed_defaults()
    application, _config = build_application()
    if args.check:
        asyncio.run(_startup_check())
        return
    application.run_polling()


if __name__ == "__main__":
    main()
