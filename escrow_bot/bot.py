from __future__ import annotations

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from escrow_bot import constants, db, repositories, services
from escrow_bot.config import load_settings
from escrow_bot.logging_config import setup_logging
from escrow_bot.models import utc_now

logger = logging.getLogger(__name__)

ROLE, COUNTERPARTY, TITLE, DESCRIPTION, PROOF, CURRENCY, AMOUNT, CONFIRM = range(8)


def _is_admin(user_id: int, admin_ids: list[int]) -> bool:
    return user_id in admin_ids


def _user_context(update: Update, admin_ids: list[int]) -> services.UserContext:
    user = update.effective_user
    return services.UserContext(user_id=user.id, username=user.username, is_admin=_is_admin(user.id, admin_ids))


def _deal_summary(data: dict, fee_amount: float) -> str:
    return (
        "<b>Deal Summary</b>\n"
        f"Role: {data['role']}\n"
        f"Counterparty: @{data['counterparty']}\n"
        f"Title: {data['title']}\n"
        f"Description: {data['description']}\n"
        f"Deadline: {data.get('deadline') or 'Not set'}\n"
        f"Proof types: {', '.join(data['proof_types'])}\n"
        f"Currency: {data['currency']} ({data['network']})\n"
        f"Amount: {data['amount']}\n"
        f"Fee: {fee_amount}\n\n"
        f"{constants.DEAL_RULE}\n"
        f"{constants.WARNING_NETWORK}\n"
    )


def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("New Deal", callback_data="start_newdeal")],
        [InlineKeyboardButton("Help", callback_data="start_help")],
    ]
    update.message.reply_text(constants.START_MESSAGE, reply_markup=InlineKeyboardMarkup(keyboard))


def start_buttons(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == "start_newdeal":
        query.message.reply_text("Select your role:", reply_markup=_role_keyboard())
        return ROLE
    query.message.reply_text("Use /newdeal to start a deal or /admin if you are an admin.")
    return ConversationHandler.END


def new_deal(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Select your role:", reply_markup=_role_keyboard())
    return ROLE


def _role_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Buyer", callback_data="role_buyer")],
            [InlineKeyboardButton("Seller", callback_data="role_seller")],
        ]
    )


def role_selected(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    role = "buyer" if query.data == "role_buyer" else "seller"
    context.user_data["deal"] = {"role": role}
    query.message.reply_text("Enter counterparty @username (without spaces):")
    return COUNTERPARTY


def counterparty_received(update: Update, context: CallbackContext) -> int:
    username = update.message.text.strip().lstrip("@").lower()
    if not username or " " in username:
        update.message.reply_text("Please provide a valid @username.")
        return COUNTERPARTY
    context.user_data["deal"]["counterparty"] = username
    update.message.reply_text("Enter deal title (at least 5 characters):")
    return TITLE


def title_received(update: Update, context: CallbackContext) -> int:
    title = update.message.text.strip()
    if len(title) < 5:
        update.message.reply_text("Title is too short. Please enter at least 5 characters.")
        return TITLE
    context.user_data["deal"]["title"] = title
    update.message.reply_text(
        "Enter full deal description. Include: what is delivered, how, and when."
    )
    return DESCRIPTION


def description_received(update: Update, context: CallbackContext) -> int:
    description = update.message.text.strip()
    try:
        services._validate_description(description)
    except services.ValidationError as exc:
        update.message.reply_text(str(exc))
        return DESCRIPTION
    context.user_data["deal"]["description"] = description
    update.message.reply_text("Select accepted proof types:", reply_markup=_proof_keyboard())
    context.user_data["deal"]["proof_types"] = []
    return PROOF


def _proof_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(item, callback_data=f"proof_{index}")] for index, item in enumerate(constants.PROOF_TYPES)]
    buttons.append([InlineKeyboardButton("Done", callback_data="proof_done")])
    return InlineKeyboardMarkup(buttons)


def proof_selected(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == "proof_done":
        if not context.user_data["deal"]["proof_types"]:
            query.message.reply_text("Select at least one proof type.")
            return PROOF
        query.message.reply_text("Select currency & network:", reply_markup=_currency_keyboard())
        return CURRENCY
    index = int(query.data.split("_")[1])
    proof = constants.PROOF_TYPES[index]
    if proof not in context.user_data["deal"]["proof_types"]:
        context.user_data["deal"]["proof_types"].append(proof)
    query.message.reply_text(f"Added: {proof}. Select more or press Done.")
    return PROOF


def _currency_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"currency_{code}")] for code, label in constants.SUPPORTED_CURRENCIES]
    )


def currency_selected(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    selection = query.data.split("_")[1]
    mapping = {
        "TON": ("TON", "TON"),
        "USDT_TON": ("USDT", "TON"),
        "USDT_TRC20": ("USDT", "TRON"),
    }
    currency, network = mapping[selection]
    context.user_data["deal"]["currency"] = currency
    context.user_data["deal"]["network"] = network
    query.message.reply_text(
        f"Enter deal amount. {constants.WARNING_NETWORK}")
    return AMOUNT


def amount_received(update: Update, context: CallbackContext) -> int:
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        update.message.reply_text("Enter a numeric amount.")
        return AMOUNT
    if amount <= 0:
        update.message.reply_text("Amount must be positive.")
        return AMOUNT
    context.user_data["deal"]["amount"] = amount

    settings = context.bot_data["settings"]
    fee_amount = services.calculate_fee(amount, services.FeeConfig(settings.fee_percent, settings.fee_flat))
    summary = _deal_summary(context.user_data["deal"], fee_amount)
    update.message.reply_text(
        summary + "\n" + constants.IRREVERSIBLE_WARNING,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Confirm", callback_data="confirm_deal")],
                [InlineKeyboardButton("Cancel", callback_data="cancel_deal")],
            ]
        ),
    )
    return CONFIRM


def confirm_deal(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == "cancel_deal":
        query.message.reply_text("Deal creation cancelled.")
        return ConversationHandler.END

    settings = context.bot_data["settings"]
    conn = context.bot_data["db"]
    user_ctx = _user_context(update, settings.admin_ids)
    repositories.upsert_user(conn, user_ctx.user_id, user_ctx.username, utc_now())
    data = context.user_data.get("deal", {})

    buyer_id = user_ctx.user_id if data["role"] == "buyer" else None
    seller_id = user_ctx.user_id if data["role"] == "seller" else None

    counterparty_username = data["counterparty"]
    counterparty_id = _lookup_user_id_by_username(conn, counterparty_username)
    if not counterparty_id:
        query.message.reply_text(
            "Counterparty must start the bot first. Ask them to /start, then retry."
        )
        return ConversationHandler.END
    if buyer_id is None:
        buyer_id = counterparty_id
    if seller_id is None:
        seller_id = counterparty_id

    deal = services.create_deal(
        conn,
        user_ctx,
        buyer_id,
        seller_id,
        data["title"],
        data["description"],
        None,
        data["proof_types"],
        data["currency"],
        data["network"],
        data["amount"],
        services.FeeConfig(settings.fee_percent, settings.fee_flat),
        services.Limits(
            settings.max_deal_amount,
            settings.max_active_deals_per_user,
            settings.deal_create_rate_limit_seconds,
        ),
    )
    query.message.reply_text(
        f"Deal created: {deal.id}. Waiting for the other party to confirm."
    )
    context.bot.send_message(
        chat_id=counterparty_id,
        text=(
            "You have a pending escrow deal. Use /confirmdeal "
            f"{deal.id} to review and confirm."
        ),
    )
    return ConversationHandler.END


def confirm_deal_command(update: Update, context: CallbackContext) -> None:
    settings = context.bot_data["settings"]
    conn = context.bot_data["db"]
    user_ctx = _user_context(update, settings.admin_ids)
    if not context.args:
        update.message.reply_text("Usage: /confirmdeal <deal_id>")
        return
    deal_id = context.args[0]
    try:
        deal = services.confirm_deal(conn, user_ctx, deal_id)
    except services.EscrowError as exc:
        update.message.reply_text(str(exc))
        return
    status = "CONFIRMED" if deal.status == "CONFIRMED" else "PENDING_OTHER_PARTY"
    update.message.reply_text(f"Deal confirmation recorded. Status: {status}.")


def deliver_request(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        update.message.reply_text("Usage: /deliver <deal_id> <proof>")
        return
    deal_id = context.args[0]
    proof = " ".join(context.args[1:])
    context.user_data["pending_action"] = {"action": "deliver", "deal_id": deal_id, "proof": proof}
    update.message.reply_text(
        constants.IRREVERSIBLE_WARNING,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Confirm delivery", callback_data="confirm_deliver")]]
        ),
    )


def release_request(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 1:
        update.message.reply_text("Usage: /release <deal_id>")
        return
    deal_id = context.args[0]
    context.user_data["pending_action"] = {"action": "release", "deal_id": deal_id}
    update.message.reply_text(
        constants.IRREVERSIBLE_WARNING,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Confirm release", callback_data="confirm_release")]]
        ),
    )


def dispute_request(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        update.message.reply_text("Usage: /dispute <deal_id> <reason>")
        return
    deal_id = context.args[0]
    reason = " ".join(context.args[1:])
    context.user_data["pending_action"] = {"action": "dispute", "deal_id": deal_id, "reason": reason}
    update.message.reply_text(
        constants.IRREVERSIBLE_WARNING,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Confirm dispute", callback_data="confirm_dispute")]]
        ),
    )


def confirm_action(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    settings = context.bot_data["settings"]
    conn = context.bot_data["db"]
    user_ctx = _user_context(update, settings.admin_ids)
    pending = context.user_data.get("pending_action")
    if not pending:
        query.message.reply_text("No pending action.")
        return
    action = pending.get("action")
    try:
        if action == "deliver":
            deal = services.mark_delivered(conn, user_ctx, pending["deal_id"], pending["proof"])
            query.message.reply_text(f"Delivery recorded. Status: {deal.status}.")
        elif action == "release":
            deal = services.release_funds(conn, user_ctx, pending["deal_id"])
            query.message.reply_text(f"Release recorded. Status: {deal.status}.")
        elif action == "dispute":
            dispute = services.open_dispute(conn, user_ctx, pending["deal_id"], pending["reason"])
            query.message.reply_text(f"Dispute opened: {dispute.id}.")
        else:
            query.message.reply_text("Unknown action.")
    except services.EscrowError as exc:
        query.message.reply_text(str(exc))
    context.user_data.pop("pending_action", None)


def admin_dashboard(update: Update, context: CallbackContext) -> None:
    settings = context.bot_data["settings"]
    user_ctx = _user_context(update, settings.admin_ids)
    if not user_ctx.is_admin:
        update.message.reply_text("Admin access required.")
        return
    update.message.reply_text("Admin dashboard: use /admindeal <deal_id> or /adminrelease <deal_id>.")


def admin_release(update: Update, context: CallbackContext) -> None:
    settings = context.bot_data["settings"]
    conn = context.bot_data["db"]
    user_ctx = _user_context(update, settings.admin_ids)
    if not user_ctx.is_admin:
        update.message.reply_text("Admin access required.")
        return
    if not context.args:
        update.message.reply_text("Usage: /adminrelease <deal_id>")
        return
    deal_id = context.args[0]
    try:
        deal = services.release_funds(conn, user_ctx, deal_id)
    except services.EscrowError as exc:
        update.message.reply_text(str(exc))
        return
    update.message.reply_text(f"Deal released. Status: {deal.status}.")


def admin_dispute(update: Update, context: CallbackContext) -> None:
    settings = context.bot_data["settings"]
    conn = context.bot_data["db"]
    user_ctx = _user_context(update, settings.admin_ids)
    if not user_ctx.is_admin:
        update.message.reply_text("Admin access required.")
        return
    if len(context.args) < 2:
        update.message.reply_text("Usage: /admindispute <deal_id> <resolution>")
        return
    deal_id = context.args[0]
    resolution = " ".join(context.args[1:])
    try:
        deal = services.resolve_dispute(conn, user_ctx, deal_id, resolution, "CLOSED")
    except services.EscrowError as exc:
        update.message.reply_text(str(exc))
        return
    update.message.reply_text(f"Dispute resolved. Deal status: {deal.status}.")


def deposit_instructions(update: Update, context: CallbackContext) -> None:
    settings = context.bot_data["settings"]
    conn = context.bot_data["db"]
    if not context.args:
        update.message.reply_text("Usage: /deposit <deal_id>")
        return
    deal_id = context.args[0]
    deal = repositories.get_deal(conn, deal_id)
    if not deal:
        update.message.reply_text("Deal not found.")
        return
    address = _deposit_address_for_deal(settings, deal.currency, deal.network)
    if not address:
        update.message.reply_text("Deposit address not configured. Contact admin.")
        return
    update.message.reply_text(
        f"Send exactly {deal.amount} {deal.currency} on {deal.network} to:\n{address}\n\n"
        f"{constants.WARNING_NETWORK}"
    )


def mock_deposit(update: Update, context: CallbackContext) -> None:
    settings = context.bot_data["settings"]
    if not settings.mock_blockchain:
        update.message.reply_text("Mock blockchain mode is disabled.")
        return
    conn = context.bot_data["db"]
    user_ctx = _user_context(update, settings.admin_ids)
    if len(context.args) < 1:
        update.message.reply_text("Usage: /mockdeposit <deal_id> [tx_hash]")
        return
    deal_id = context.args[0]
    tx_hash = context.args[1] if len(context.args) > 1 else "mock-tx"
    try:
        payment = services.mark_funded(conn, user_ctx, deal_id, tx_hash=tx_hash)
    except services.EscrowError as exc:
        update.message.reply_text(str(exc))
        return
    update.message.reply_text(f"Mock deposit recorded: {payment.tx_hash}.")


def _deposit_address_for_deal(settings, currency: str, network: str) -> str:
    if currency == "TON" and network == "TON":
        return settings.ton_deposit_address
    if currency == "USDT" and network == "TON":
        return settings.usdt_ton_deposit_address
    if currency == "USDT" and network == "TRON":
        return settings.usdt_tron_deposit_address
    return ""


def _lookup_user_id_by_username(conn, username: str) -> int | None:
    row = db.fetch_one(conn, "SELECT id FROM users WHERE username=?", (username,))
    return row["id"] if row else None


def error_handler(update: object, context: CallbackContext) -> None:
    logger.exception("Unhandled error", exc_info=context.error)


def build_application() -> Application:
    settings = load_settings()
    setup_logging(settings.log_level)
    conn = db.connect(settings.database_path)
    db.init_db(conn)

    application = Application.builder().token(settings.bot_token).build()
    application.bot_data["db"] = conn
    application.bot_data["settings"] = settings

    conversation = ConversationHandler(
        entry_points=[CommandHandler("newdeal", new_deal), CallbackQueryHandler(start_buttons, pattern="^start_")],
        states={
            ROLE: [CallbackQueryHandler(role_selected, pattern="^role_")],
            COUNTERPARTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, counterparty_received)],
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title_received)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_received)],
            PROOF: [CallbackQueryHandler(proof_selected, pattern="^proof_")],
            CURRENCY: [CallbackQueryHandler(currency_selected, pattern="^currency_")],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_received)],
            CONFIRM: [CallbackQueryHandler(confirm_deal, pattern="^(confirm_deal|cancel_deal)$")],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conversation)
    application.add_handler(CommandHandler("confirmdeal", confirm_deal_command))
    application.add_handler(CommandHandler("deliver", deliver_request))
    application.add_handler(CommandHandler("release", release_request))
    application.add_handler(CommandHandler("dispute", dispute_request))
    application.add_handler(CommandHandler("admin", admin_dashboard))
    application.add_handler(CommandHandler("adminrelease", admin_release))
    application.add_handler(CommandHandler("admindispute", admin_dispute))
    application.add_handler(CommandHandler("deposit", deposit_instructions))
    application.add_handler(CommandHandler("mockdeposit", mock_deposit))
    application.add_handler(CallbackQueryHandler(confirm_action, pattern="^confirm_(deliver|release|dispute)$"))
    application.add_error_handler(error_handler)

    return application


def main() -> None:
    application = build_application()
    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
