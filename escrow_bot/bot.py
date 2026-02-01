from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from escrow_bot import constants, db, repositories, services, ui_text
from escrow_bot.config import load_settings
from escrow_bot.deposit_service import DepositExpectation, fetch_ton_transactions, fetch_tron_transaction, format_ton_memo, parse_ton_transactions, ton_tx_matches, tron_usdt_matches
from escrow_bot.logging_config import setup_logging
from escrow_bot.logging_service import log_event
from escrow_bot.models import utc_now
from escrow_bot.settings_store import ensure_defaults, get_bool, get_float, get_int, get_setting, set_setting, toggle_setting

logger = logging.getLogger(__name__)

ROLE, COUNTERPARTY, TITLE, DESCRIPTION, PROOF, CURRENCY, AMOUNT, CONFIRM, ACTION_INPUT, ADMIN_EDIT = range(10)


def _build_keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=callback) for label, callback in row] for row in rows]
    )


def _admin_only_text() -> str:
    return "<b>Admin access required.</b>"


def _is_private_chat(update: Update) -> bool:
    chat = update.effective_chat
    return chat and chat.type == "private"


def _user_context(update: Update, admin_ids: list[int]) -> services.UserContext:
    user = update.effective_user
    return services.UserContext(user_id=user.id, username=user.username, is_admin=user.id in admin_ids)


async def _send_html(message, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    await message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


def _settings_defaults(settings) -> dict[str, Any]:
    return {
        "fee_percent": settings.fee_percent,
        "fee_flat": settings.fee_flat,
        "max_deal_amount": settings.max_deal_amount,
        "max_active_deals_per_user": settings.max_active_deals_per_user,
        "rate_limit_seconds": settings.deal_create_rate_limit_seconds,
        "ton_deposit_address": settings.ton_deposit_address,
        "usdt_ton_deposit_address": settings.usdt_ton_deposit_address,
        "usdt_trc20_deposit_address": settings.usdt_tron_deposit_address,
        "fee_wallet_ton": settings.fee_wallet_ton,
        "fee_wallet_usdt_ton": settings.fee_wallet_usdt_ton,
        "fee_wallet_usdt_trc20": settings.fee_wallet_usdt_trc20,
        "updates_channel_url": settings.updates_channel_url,
        "vouches_channel_url": settings.vouches_channel_url,
        "support_username_or_url": settings.support_username_or_url,
        "private_log_channel_id": settings.private_log_channel_id,
        "public_log_channel_id": settings.public_log_channel_id,
        "confirmations_required_ton": settings.confirmations_required_ton,
        "confirmations_required_tron": settings.confirmations_required_tron,
        "maintenance_mode": "false",
        "logs_private_enabled": "false",
        "logs_public_enabled": "false",
        "public_masking_mode": "masked",
        "log_event_deal_created": "true",
        "log_event_deal_confirmed": "true",
        "log_event_deal_funded": "true",
        "log_event_deal_delivered": "true",
        "log_event_deal_released": "true",
        "log_event_deal_refunded": "true",
        "log_event_deal_disputed": "true",
        "log_event_admin_actions": "true",
        "ton_api_url": settings.ton_api_url,
        "ton_api_key": settings.ton_api_key,
        "tron_api_url": settings.tron_api_url,
    }


def _fee_config(conn) -> services.FeeConfig:
    return services.FeeConfig(
        percent=get_float(conn, "fee_percent", 1.0),
        flat=get_float(conn, "fee_flat", 0.0),
    )


def _limits_config(conn) -> services.Limits:
    return services.Limits(
        max_amount=get_float(conn, "max_deal_amount", 10000),
        max_active_deals=get_int(conn, "max_active_deals_per_user", 5),
        deal_create_rate_limit_seconds=get_int(conn, "rate_limit_seconds", 60),
    )


def _fee_summary(amount: float, fee_cfg: services.FeeConfig) -> tuple[float, float]:
    fee = services.calculate_fee(amount, fee_cfg)
    return fee, round(amount - fee, 8)


def _wallet_mask(value: str | None) -> str:
    if not value:
        return "—"
    return value[:4] + "..." + value[-4:]


def _deal_to_dict(deal) -> dict:
    data = asdict(deal)
    data["proof_types"] = list(deal.proof_types)
    return data


def _proof_keyboard(selected: list[int]) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    for index, _label in enumerate(constants.PROOF_TYPES):
        rows.append([(ui_text.proof_toggle_label(index, index in selected), f"proof_toggle:{index}")])
    rows.append([("Continue ➡️", "proof_continue"), ("⬅️ Back", "proof_back")])
    rows.append([("🏠 Menu", "menu_home")])
    return _build_keyboard(rows)


def _role_keyboard() -> InlineKeyboardMarkup:
    return _build_keyboard(
        [
            [("Buyer", "role_buyer"), ("Seller", "role_seller")],
            [("⬅️ Back", "menu_home"), ("🏠 Menu", "menu_home")],
        ]
    )


def _currency_keyboard() -> InlineKeyboardMarkup:
    rows = [[(label, f"currency_{code}")] for code, label in constants.SUPPORTED_CURRENCIES]
    rows.append([("⬅️ Back", "currency_back"), ("🏠 Menu", "menu_home")])
    return _build_keyboard(rows)


def _back_menu_keyboard(back: str) -> InlineKeyboardMarkup:
    return _build_keyboard(ui_text.back_menu_buttons(back))


def _deal_action_keyboard(deal: dict, user_ctx: services.UserContext, show_full: bool) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    if deal["status"] == "CONFIRMED" and user_ctx.user_id == deal["buyer_id"]:
        rows.append([("💳 Deposit Instructions", f"deal_deposit:{deal['id']}")])
        if deal["currency"] == "USDT" and deal["network"] == "TRON":
            rows.append([("🧾 Submit Tx Hash", f"deal_submit_tx:{deal['id']}")])
    if deal["status"] == "FUNDED" and user_ctx.user_id == deal["seller_id"]:
        rows.append([("📦 Mark Delivered", f"deal_mark_delivered:{deal['id']}")])
    if deal["status"] == "DELIVERED" and user_ctx.user_id == deal["buyer_id"]:
        rows.append([("✅ Release Funds", f"deal_release:{deal['id']}")])
    if deal["status"] in {"FUNDED", "DELIVERED"} and user_ctx.user_id in {deal["buyer_id"], deal["seller_id"]}:
        rows.append([("⚖️ Open Dispute", f"deal_dispute:{deal['id']}")])
    if deal["status"] == "DISPUTED" and user_ctx.is_admin:
        rows.append([("🧑‍⚖️ Resolve", f"deal_resolve:{deal['id']}")])
    if deal["status"] == "RELEASED" and user_ctx.is_admin:
        rows.append([("💸 Execute Payout", f"deal_payout:{deal['id']}")])
        rows.append([("🔒 Close Deal", f"deal_close:{deal['id']}")])
    if len(deal["description"]) > 240:
        label = "Show Less" if show_full else "Show More"
        rows.append([(label, f"deal_toggle_terms:{deal['id']}")])
    rows.append([("⬅️ Back to My Deals", "menu_mydeals"), ("🏠 Menu", "menu_home")])
    return _build_keyboard(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private_chat(update):
        await _send_html(update.effective_message, "<b>Use this bot in private chat only.</b>")
        return
    conn = context.bot_data["db"]
    fee_percent = get_float(conn, "fee_percent", 1.0)
    await _send_html(update.effective_message, ui_text.main_menu_text(fee_percent), _build_keyboard(ui_text.menu_buttons()))


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    conn = context.bot_data["db"]
    data = query.data
    if data == "menu_home":
        fee_percent = get_float(conn, "fee_percent", 1.0)
        await _send_html(query.message, ui_text.main_menu_text(fee_percent), _build_keyboard(ui_text.menu_buttons()))
        return ConversationHandler.END
    if data == "menu_newdeal":
        if get_bool(conn, "maintenance_mode", False):
            await _send_html(query.message, "<b>Maintenance mode is ON.</b> New deals are paused.", _back_menu_keyboard("menu_home"))
            return ConversationHandler.END
        await _send_html(query.message, "<b>Select your role:</b>", _role_keyboard())
        return ROLE
    if data == "menu_mydeals":
        user_ctx = _user_context(update, context.bot_data["settings"].admin_ids)
        deals = repositories.list_user_deals(conn, user_ctx.user_id, limit=10)
        if not deals:
            await _send_html(query.message, "<b>📂 Your Deals</b>\n\nNo deals yet.", _back_menu_keyboard("menu_home"))
            return ConversationHandler.END
        items = [_deal_to_dict(deal) for deal in deals]
        await _send_html(query.message, ui_text.render_deal_list(items), _my_deals_keyboard(items))
        return ConversationHandler.END
    if data == "menu_deposit_help":
        await _send_html(query.message, ui_text.deposit_help_text(), _back_menu_keyboard("menu_home"))
        return ConversationHandler.END
    if data == "menu_fees":
        fee_percent = get_float(conn, "fee_percent", 1.0)
        fee_flat = get_float(conn, "fee_flat", 0.0)
        wallet_info = "TON " + _wallet_mask(get_setting(conn, "fee_wallet_ton"))
        wallet_info += " | USDT-TON " + _wallet_mask(get_setting(conn, "fee_wallet_usdt_ton"))
        wallet_info += " | USDT-TRC20 " + _wallet_mask(get_setting(conn, "fee_wallet_usdt_trc20"))
        await _send_html(query.message, ui_text.fees_text(fee_percent, fee_flat, wallet_info), _back_menu_keyboard("menu_home"))
        return ConversationHandler.END
    if data == "menu_updates":
        url = get_setting(conn, "updates_channel_url")
        await _send_html(query.message, ui_text.updates_text(url), _info_link_keyboard(url, "menu_home"))
        return ConversationHandler.END
    if data == "menu_vouches":
        url = get_setting(conn, "vouches_channel_url")
        await _send_html(query.message, ui_text.vouches_text(url), _info_link_keyboard(url, "menu_home"))
        return ConversationHandler.END
    if data == "menu_how":
        await _send_html(query.message, ui_text.how_text(), _back_menu_keyboard("menu_home"))
        return ConversationHandler.END
    if data == "menu_terms":
        await _send_html(query.message, ui_text.terms_text(), _back_menu_keyboard("menu_home"))
        return ConversationHandler.END
    if data == "menu_support":
        await _send_html(query.message, ui_text.support_text(get_setting(conn, "support_username_or_url")), _back_menu_keyboard("menu_home"))
        return ConversationHandler.END
    return ConversationHandler.END


async def newdeal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_private_chat(update):
        await _send_html(update.effective_message, "<b>Use this bot in private chat only.</b>")
        return ConversationHandler.END
    conn = context.bot_data["db"]
    if get_bool(conn, "maintenance_mode", False):
        await _send_html(update.effective_message, "<b>Maintenance mode is ON.</b> New deals are paused.", _back_menu_keyboard("menu_home"))
        return ConversationHandler.END
    await _send_html(update.effective_message, "<b>Select your role:</b>", _role_keyboard())
    return ROLE


async def mydeals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private_chat(update):
        await _send_html(update.effective_message, "<b>Use this bot in private chat only.</b>")
        return
    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    user_ctx = _user_context(update, settings.admin_ids)
    deals = repositories.list_user_deals(conn, user_ctx.user_id, limit=10)
    if not deals:
        await _send_html(update.effective_message, "<b>📂 Your Deals</b>\n\nNo deals yet.", _back_menu_keyboard("menu_home"))
        return
    items = [_deal_to_dict(deal) for deal in deals]
    await _send_html(update.effective_message, ui_text.render_deal_list(items), _my_deals_keyboard(items))


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private_chat(update):
        await _send_html(update.effective_message, "<b>Use this bot in private chat only.</b>")
        return
    if not context.args:
        await _send_html(update.effective_message, "Usage: /deposit <deal_id>")
        return
    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    user_ctx = _user_context(update, settings.admin_ids)
    deal = repositories.get_deal(conn, context.args[0])
    if not deal or user_ctx.user_id != deal.buyer_id:
        await _send_html(update.effective_message, "⚠️ Only buyer can view deposit instructions.")
        return
    await _send_deposit_instructions(update.effective_message, conn, deal, f"deal_open:{deal.id}")


async def deliver_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private_chat(update):
        await _send_html(update.effective_message, "<b>Use this bot in private chat only.</b>")
        return
    if len(context.args) < 2:
        await _send_html(update.effective_message, "Usage: /deliver <deal_id> <proof>")
        return
    deal_id = context.args[0]
    proof = " ".join(context.args[1:])
    context.user_data["confirm_action"] = {"action": "deliver", "deal_id": deal_id, "proof": proof}
    await _send_html(
        update.effective_message,
        "<b>Confirm delivery?</b>",
        _build_keyboard([[("✅ Confirm", f"confirm_action:{deal_id}:deliver"), ("❌ Cancel", f"deal_open:{deal_id}")]]),
    )


async def release_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private_chat(update):
        await _send_html(update.effective_message, "<b>Use this bot in private chat only.</b>")
        return
    if len(context.args) < 1:
        await _send_html(update.effective_message, "Usage: /release <deal_id>")
        return
    deal_id = context.args[0]
    context.user_data["confirm_action"] = {"action": "release", "deal_id": deal_id}
    await _send_html(
        update.effective_message,
        "<b>Confirm release?</b>",
        _build_keyboard([[("✅ Confirm", f"confirm_action:{deal_id}:release"), ("❌ Cancel", f"deal_open:{deal_id}")]]),
    )


async def dispute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private_chat(update):
        await _send_html(update.effective_message, "<b>Use this bot in private chat only.</b>")
        return
    if len(context.args) < 2:
        await _send_html(update.effective_message, "Usage: /dispute <deal_id> <reason>")
        return
    deal_id = context.args[0]
    reason = " ".join(context.args[1:])
    context.user_data["confirm_action"] = {"action": "dispute", "deal_id": deal_id, "reason": reason}
    await _send_html(
        update.effective_message,
        "<b>Confirm dispute?</b>",
        _build_keyboard([[("✅ Confirm", f"confirm_action:{deal_id}:dispute"), ("❌ Cancel", f"deal_open:{deal_id}")]]),
    )


async def submit_tx_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private_chat(update):
        await _send_html(update.effective_message, "<b>Use this bot in private chat only.</b>")
        return
    if len(context.args) < 2:
        await _send_html(update.effective_message, "Usage: /submittx <deal_id> <tx_hash>")
        return
    deal_id = context.args[0]
    tx_hash = context.args[1]
    context.user_data["confirm_action"] = {"action": "submit_tx", "deal_id": deal_id, "tx_hash": tx_hash}
    await _send_html(
        update.effective_message,
        "<b>Confirm tx hash?</b>",
        _build_keyboard([[("✅ Confirm", f"confirm_action:{deal_id}:submit_tx"), ("❌ Cancel", f"deal_open:{deal_id}")]]),
    )


async def mockdeposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data["settings"]
    if not settings.mock_blockchain:
        await _send_html(update.effective_message, "Mock blockchain mode is disabled.")
        return
    if len(context.args) < 1:
        await _send_html(update.effective_message, "Usage: /mockdeposit <deal_id> [tx_hash]")
        return
    conn = context.bot_data["db"]
    user_ctx = _user_context(update, settings.admin_ids)
    tx_hash = context.args[1] if len(context.args) > 1 else "mock-tx"
    try:
        payment = services.mark_funded(conn, user_ctx, context.args[0], tx_hash=tx_hash)
    except services.EscrowError as exc:
        await _send_html(update.effective_message, str(exc))
        return
    await _send_html(update.effective_message, f"Mock deposit recorded: <code>{payment.tx_hash}</code>.")
    deal = repositories.get_deal(conn, context.args[0])
    if deal:
        log_event(
            context.bot,
            conn,
            settings.admin_ids,
            "Deal Funded",
            "deal_funded",
            _deal_to_dict(deal),
            {\"buyer\": repositories.get_username(conn, deal.buyer_id), \"seller\": repositories.get_username(conn, deal.seller_id), \"tx_hash\": payment.tx_hash},
        )


def _my_deals_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    for deal in items:
        rows.append([(f"Open {deal['id']}", f"deal_open:{deal['id']}")])
    rows.append([("⬅️ Back", "menu_home"), ("🏠 Menu", "menu_home")])
    return _build_keyboard(rows)


def _info_link_keyboard(url: str | None, back: str) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    if url:
        rows.append([("Open", url)])
    rows.append([("⬅️ Back", back), ("🏠 Menu", "menu_home")])
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=callback) if not callback.startswith("http") else InlineKeyboardButton(label, url=callback) for label, callback in row] for row in rows]
    )


async def role_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    role = "buyer" if query.data == "role_buyer" else "seller"
    context.user_data["deal"] = {"role": role}
    await _send_html(query.message, "<b>Enter counterparty @username:</b>", _back_menu_keyboard("menu_home"))
    return COUNTERPARTY


async def counterparty_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip().lstrip("@").lower()
    if not username or " " in username:
        await _send_html(update.message, "⚠️ Please provide a valid @username.")
        return COUNTERPARTY
    context.user_data["deal"]["counterparty"] = username
    await _send_html(update.message, "<b>Enter deal title (5+ chars):</b>", _back_menu_keyboard("menu_home"))
    return TITLE


async def title_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    title = update.message.text.strip()
    if len(title) < 5:
        await _send_html(update.message, "⚠️ Title too short.")
        return TITLE
    context.user_data["deal"]["title"] = title
    await _send_html(update.message, "<b>Write clear terms.</b> What you deliver, how, and completion.", _back_menu_keyboard("menu_home"))
    return DESCRIPTION


async def description_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    description = update.message.text.strip()
    try:
        services._validate_description(description)
    except services.ValidationError:
        await _send_html(update.message, "⚠️ Write clear terms: what you deliver, how, and what counts as complete.")
        return DESCRIPTION
    context.user_data["deal"]["description"] = description
    context.user_data["deal"]["proof_types"] = []
    await _send_html(update.message, "<b>Select proof types:</b>", _proof_keyboard([]))
    return PROOF


async def proof_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selection = context.user_data["deal"]["proof_types"]
    if query.data == "proof_continue":
        if not selection:
            await _send_html(query.message, "⚠️ Select at least one proof type.", _proof_keyboard(selection))
            return PROOF
        await _send_html(query.message, "<b>Select currency & network:</b>", _currency_keyboard())
        return CURRENCY
    if query.data == "proof_back":
        await _send_html(query.message, "<b>Enter deal description again:</b>")
        return DESCRIPTION
    if query.data.startswith("proof_toggle:"):
        index = int(query.data.split(":")[1])
        if index in selection:
            selection.remove(index)
        else:
            selection.append(index)
        context.user_data["deal"]["proof_types"] = selection
        await _send_html(query.message, "<b>Select proof types:</b>", _proof_keyboard(selection))
        return PROOF
    return PROOF


async def currency_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "currency_back":
        await _send_html(query.message, "<b>Select proof types:</b>", _proof_keyboard(context.user_data["deal"]["proof_types"]))
        return PROOF
    selection = query.data.split("_")[1]
    mapping = {
        "TON": ("TON", "TON"),
        "USDT_TON": ("USDT", "TON"),
        "USDT_TRC20": ("USDT", "TRON"),
    }
    currency, network = mapping[selection]
    context.user_data["deal"]["currency"] = currency
    context.user_data["deal"]["network"] = network
    await _send_html(query.message, "<b>Enter deal amount:</b>", _back_menu_keyboard("menu_home"))
    return AMOUNT


async def amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await _send_html(update.message, "⚠️ Enter a numeric amount.")
        return AMOUNT
    if amount <= 0:
        await _send_html(update.message, "⚠️ Amount must be positive.")
        return AMOUNT
    context.user_data["deal"]["amount"] = amount

    conn = context.bot_data["db"]
    fee_cfg = _fee_config(conn)
    fee, seller_receives = _fee_summary(amount, fee_cfg)
    data = context.user_data["deal"]
    proof_labels = [constants.PROOF_TYPES[index] for index in data["proof_types"]]
    summary = (
        "<b>🧾 Deal Summary</b>\n"
        f"• Role: {data['role']}\n"
        f"• Counterparty: @{data['counterparty']}\n"
        f"• Title: {data['title']}\n"
        f"• Description: {data['description']}\n"
        f"• Proof: {', '.join(proof_labels)}\n"
        f"• Currency: {data['currency']} ({data['network']})\n"
        f"• Amount: {amount}\n"
        f"• Fee: {fee}\n"
        f"• Seller receives: {seller_receives}\n\n"
        "⚠️ Wrong network = funds lost forever\n"
        "<b>Rule:</b> If it’s not written, it doesn’t exist."
    )
    await _send_html(
        update.message,
        summary,
        _build_keyboard(
            [[("Confirm", "confirm_deal"), ("Cancel", "cancel_deal")], [("⬅️ Back", "menu_newdeal"), ("🏠 Menu", "menu_home")]]
        ),
    )
    return CONFIRM


async def confirm_deal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "cancel_deal":
        await _send_html(query.message, "Deal creation cancelled.", _back_menu_keyboard("menu_home"))
        return ConversationHandler.END

    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    user_ctx = _user_context(update, settings.admin_ids)
    repositories.upsert_user(conn, user_ctx.user_id, user_ctx.username, utc_now())

    data = context.user_data.get("deal", {})
    buyer_id = user_ctx.user_id if data["role"] == "buyer" else None
    seller_id = user_ctx.user_id if data["role"] == "seller" else None

    counterparty_username = data["counterparty"]
    counterparty_id = _lookup_user_id_by_username(conn, counterparty_username)
    if not counterparty_id:
        await _send_html(query.message, "Counterparty must start the bot first. Ask them to /start.")
        return ConversationHandler.END
    if buyer_id is None:
        buyer_id = counterparty_id
    if seller_id is None:
        seller_id = counterparty_id

    fee_cfg = _fee_config(conn)
    limits = _limits_config(conn)
    proof_labels = [constants.PROOF_TYPES[index] for index in data["proof_types"]]

    try:
        deal = services.create_deal(
            conn,
            user_ctx,
            buyer_id,
            seller_id,
            data["title"],
            data["description"],
            None,
            proof_labels,
            data["currency"],
            data["network"],
            data["amount"],
            fee_cfg,
            limits,
        )
    except services.EscrowError as exc:
        await _send_html(query.message, str(exc))
        return ConversationHandler.END

    await _send_html(query.message, f"Deal created: <code>{deal.id}</code>\nWaiting for the other party to confirm.")
    await context.bot.send_message(
        chat_id=counterparty_id,
        text=(
            "<b>New deal awaiting you.</b>\n"
            f"Use /confirmdeal {deal.id} to confirm."
        ),
        parse_mode=ParseMode.HTML,
    )
    log_event(
        context.bot,
        conn,
        settings.admin_ids,
        "Deal Created",
        "deal_created",
        _deal_to_dict(deal),
        {"buyer": repositories.get_username(conn, deal.buyer_id), "seller": repositories.get_username(conn, deal.seller_id)},
    )
    return ConversationHandler.END


async def confirm_deal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    user_ctx = _user_context(update, settings.admin_ids)
    if not context.args:
        await _send_html(update.message, "Usage: /confirmdeal <deal_id>")
        return
    deal_id = context.args[0]
    try:
        deal = services.confirm_deal(conn, user_ctx, deal_id)
    except services.EscrowError as exc:
        await _send_html(update.message, str(exc))
        return
    status = "CONFIRMED" if deal.status == "CONFIRMED" else "PENDING_OTHER_PARTY"
    await _send_html(update.message, f"Deal confirmation recorded. Status: <b>{status}</b>.")
    log_event(
        context.bot,
        conn,
        settings.admin_ids,
        "Deal Confirmed",
        "deal_confirmed",
        _deal_to_dict(deal),
        {"buyer": repositories.get_username(conn, deal.buyer_id), "seller": repositories.get_username(conn, deal.seller_id)},
    )


async def deal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not _is_private_chat(update):
        await _send_html(query.message, "<b>Use this bot in private chat only.</b>")
        return ConversationHandler.END
    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    user_ctx = _user_context(update, settings.admin_ids)

    if query.data.startswith("deal_open:"):
        deal_id = query.data.split(":")[1]
        deal = repositories.get_deal(conn, deal_id)
        if not deal or user_ctx.user_id not in {deal.buyer_id, deal.seller_id} and not user_ctx.is_admin:
            await _send_html(query.message, "⚠️ Deal not found.", _back_menu_keyboard("menu_mydeals"))
            return
        show_full = context.user_data.get("show_full_terms", set())
        show_flag = deal_id in show_full
        buyer_username = repositories.get_username(conn, deal.buyer_id)
        seller_username = repositories.get_username(conn, deal.seller_id)
        await _send_html(
            query.message,
            ui_text.render_deal_details(_deal_to_dict(deal), buyer_username, seller_username, show_flag),
            _deal_action_keyboard(_deal_to_dict(deal), user_ctx, show_flag),
        )
        return

    if query.data.startswith("deal_toggle_terms:"):
        deal_id = query.data.split(":")[1]
        show_full = context.user_data.setdefault("show_full_terms", set())
        if deal_id in show_full:
            show_full.remove(deal_id)
        else:
            show_full.add(deal_id)
        deal = repositories.get_deal(conn, deal_id)
        if not deal:
            await _send_html(query.message, "⚠️ Deal not found.")
            return
        buyer_username = repositories.get_username(conn, deal.buyer_id)
        seller_username = repositories.get_username(conn, deal.seller_id)
        await _send_html(
            query.message,
            ui_text.render_deal_details(_deal_to_dict(deal), buyer_username, seller_username, deal_id in show_full),
            _deal_action_keyboard(_deal_to_dict(deal), user_ctx, deal_id in show_full),
        )
        return

    if query.data.startswith("deal_deposit:"):
        deal_id = query.data.split(":")[1]
        deal = repositories.get_deal(conn, deal_id)
        if not deal or user_ctx.user_id != deal.buyer_id:
            await _send_html(query.message, "⚠️ Only buyer can view deposit instructions.")
            return
        await _send_deposit_instructions(query.message, conn, deal, f"deal_open:{deal.id}")
        return

    if query.data.startswith("deal_submit_tx:"):
        deal_id = query.data.split(":")[1]
        deal = repositories.get_deal(conn, deal_id)
        if not deal or user_ctx.user_id != deal.buyer_id:
            await _send_html(query.message, "⚠️ Only buyer can submit tx hash.")
            return
        if deal.network != "TRON" or deal.currency != "USDT":
            await _send_html(query.message, "⚠️ Tx hash is only for USDT (TRC20).")
            return
        context.user_data["pending_action"] = {"action": "submit_tx", "deal_id": deal_id}
        await _send_html(query.message, "<b>Paste TRC20 Tx Hash:</b>", _back_menu_keyboard(f"deal_open:{deal.id}"))
        return ACTION_INPUT

    if query.data.startswith("deal_mark_delivered:"):
        deal_id = query.data.split(":")[1]
        context.user_data["pending_action"] = {"action": "deliver", "deal_id": deal_id}
        await _send_html(query.message, "<b>Provide delivery proof:</b>", _back_menu_keyboard(f"deal_open:{deal_id}"))
        return ACTION_INPUT

    if query.data.startswith("deal_release:"):
        deal_id = query.data.split(":")[1]
        context.user_data["confirm_action"] = {"action": "release", "deal_id": deal_id}
        await _send_html(
            query.message,
            "<b>Confirm release?</b>",
            _build_keyboard([[ ("✅ Confirm", f"confirm_action:{deal_id}:release"), ("❌ Cancel", f"deal_open:{deal_id}") ]]),
        )
        return ConversationHandler.END

    if query.data.startswith("deal_dispute:"):
        deal_id = query.data.split(":")[1]
        context.user_data["pending_action"] = {"action": "dispute", "deal_id": deal_id}
        await _send_html(query.message, "<b>Describe dispute:</b>", _back_menu_keyboard(f"deal_open:{deal_id}"))
        return ACTION_INPUT

    if query.data.startswith("deal_resolve:"):
        deal_id = query.data.split(":")[1]
        context.user_data["pending_action"] = {"action": "resolve", "deal_id": deal_id}
        await _send_html(query.message, "<b>Resolution notes:</b>", _back_menu_keyboard(f"deal_open:{deal_id}"))
        return ACTION_INPUT

    if query.data.startswith("deal_payout:"):
        deal_id = query.data.split(":")[1]
        context.user_data["confirm_action"] = {"action": "payout", "deal_id": deal_id}
        await _send_html(
            query.message,
            "<b>Execute payout now?</b>",
            _build_keyboard([[ ("✅ Confirm", f"confirm_action:{deal_id}:payout"), ("❌ Cancel", f"deal_open:{deal_id}") ]]),
        )
        return ConversationHandler.END

    if query.data.startswith("deal_close:"):
        deal_id = query.data.split(":")[1]
        context.user_data["confirm_action"] = {"action": "close", "deal_id": deal_id}
        await _send_html(
            query.message,
            "<b>Close this deal?</b>",
            _build_keyboard([[ ("✅ Confirm", f"confirm_action:{deal_id}:close"), ("❌ Cancel", f"deal_open:{deal_id}") ]]),
        )
        return ConversationHandler.END

    return ConversationHandler.END


async def _handle_confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str, action: str) -> None:
    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    user_ctx = _user_context(update, settings.admin_ids)
    deal = repositories.get_deal(conn, deal_id)
    if not deal:
        await _send_html(update.effective_message, "⚠️ Deal not found.")
        return
    try:
        if action == "release":
            updated = services.release_funds(conn, user_ctx, deal_id)
            await _send_html(update.effective_message, f"Release recorded. Status: {updated.status}.")
            log_event(
                context.bot,
                conn,
                settings.admin_ids,
                "Deal Released",
                "deal_released",
                _deal_to_dict(updated),
                {"buyer": repositories.get_username(conn, updated.buyer_id), "seller": repositories.get_username(conn, updated.seller_id)},
            )
        if action == "payout":
            if not user_ctx.is_admin:
                await _send_html(update.effective_message, _admin_only_text())
                return
            fee_cfg = _fee_config(conn)
            fee, seller_receives = _fee_summary(deal.amount, fee_cfg)
            wallet = _fee_wallet(conn, deal.currency, deal.network)
            repositories.log_audit(
                conn,
                "payout" + utc_now(),
                user_ctx.user_id,
                "payout_executed",
                deal_id,
                db.json_dump({"fee": fee, "seller_receives": seller_receives, "wallet": wallet}),
                utc_now(),
            )
            await _send_html(update.effective_message, f"Payout queued. Seller gets {seller_receives}. Fee to {wallet}.")
        if action == "close":
            updated = services.close_deal(conn, user_ctx, deal_id)
            await _send_html(update.effective_message, f"Deal closed. Status: {updated.status}.")
        if action in {"payout", "close"}:
            log_event(
                context.bot,
                conn,
                settings.admin_ids,
                "Admin Action",
                "admin_actions",
                _deal_to_dict(deal),
                {"buyer": repositories.get_username(conn, deal.buyer_id), "seller": repositories.get_username(conn, deal.seller_id)},
            )
    except services.EscrowError as exc:
        await _send_html(update.effective_message, str(exc))


async def pending_action_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pending = context.user_data.get("pending_action")
    if not pending:
        return ConversationHandler.END
    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    user_ctx = _user_context(update, settings.admin_ids)
    deal_id = pending["deal_id"]
    deal = repositories.get_deal(conn, deal_id)
    if not deal:
        await _send_html(update.message, "⚠️ Deal not found.")
        return ConversationHandler.END

    action = pending["action"]
    text = update.message.text.strip()
    if action == "deliver":
        context.user_data["confirm_action"] = {"action": "deliver", "deal_id": deal_id, "proof": text}
        await _send_html(
            update.message,
            "<b>Confirm delivery?</b>",
            _build_keyboard([[ ("✅ Confirm", f"confirm_action:{deal_id}:deliver"), ("❌ Cancel", f"deal_open:{deal_id}") ]]),
        )
    elif action == "dispute":
        context.user_data["confirm_action"] = {"action": "dispute", "deal_id": deal_id, "reason": text}
        await _send_html(
            update.message,
            "<b>Confirm dispute?</b>",
            _build_keyboard([[ ("✅ Confirm", f"confirm_action:{deal_id}:dispute"), ("❌ Cancel", f"deal_open:{deal_id}") ]]),
        )
    elif action == "resolve":
        context.user_data["confirm_action"] = {"action": "resolve", "deal_id": deal_id, "resolution": text}
        await _send_html(
            update.message,
            "<b>Confirm resolution?</b>",
            _build_keyboard([[ ("✅ Confirm", f"confirm_action:{deal_id}:resolve"), ("❌ Cancel", f"deal_open:{deal_id}") ]]),
        )
    elif action == "submit_tx":
        context.user_data["confirm_action"] = {"action": "submit_tx", "deal_id": deal_id, "tx_hash": text}
        await _send_html(
            update.message,
            "<b>Confirm tx hash?</b>",
            _build_keyboard([[ ("✅ Confirm", f"confirm_action:{deal_id}:submit_tx"), ("❌ Cancel", f"deal_open:{deal_id}") ]]),
        )
    context.user_data.pop("pending_action", None)
    return ConversationHandler.END


async def confirm_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    deal_id = query.data.split(":")[1]
    action = query.data.split(":")[2]
    confirm_action = context.user_data.get("confirm_action", {})
    if confirm_action.get("deal_id") != deal_id or confirm_action.get("action") != action:
        await _send_html(query.message, "⚠️ No pending action.")
        return
    try:
        if action == "deliver":
            user_ctx = _user_context(update, settings.admin_ids)
            updated = services.mark_delivered(conn, user_ctx, deal_id, confirm_action["proof"])
            await _send_html(query.message, f"Delivery recorded. Status: {updated.status}.")
            log_event(
                context.bot,
                conn,
                settings.admin_ids,
                "Deal Delivered",
                "deal_delivered",
                _deal_to_dict(updated),
                {"buyer": repositories.get_username(conn, updated.buyer_id), "seller": repositories.get_username(conn, updated.seller_id)},
            )
        elif action == "dispute":
            user_ctx = _user_context(update, settings.admin_ids)
            dispute = services.open_dispute(conn, user_ctx, deal_id, confirm_action["reason"])
            await _send_html(query.message, f"Dispute opened: <code>{dispute.id}</code>.")
            deal = repositories.get_deal(conn, deal_id)
            log_event(
                context.bot,
                conn,
                settings.admin_ids,
                "Deal Disputed",
                "deal_disputed",
                _deal_to_dict(deal),
                {"buyer": repositories.get_username(conn, deal.buyer_id), "seller": repositories.get_username(conn, deal.seller_id)},
            )
        elif action == "resolve":
            user_ctx = _user_context(update, settings.admin_ids)
            updated = services.resolve_dispute(conn, user_ctx, deal_id, confirm_action["resolution"], "CLOSED")
            await _send_html(query.message, f"Dispute resolved. Deal status: {updated.status}.")
        elif action == "submit_tx":
            await _handle_trc20_tx_submission(update, context, deal_id, confirm_action["tx_hash"])
        elif action in {"release", "payout", "close"}:
            await _handle_confirm_action(update, context, deal_id, action)
    except services.EscrowError as exc:
        await _send_html(query.message, str(exc))
    context.user_data.pop("confirm_action", None)


async def _handle_trc20_tx_submission(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str, tx_hash: str) -> None:
    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    deal = repositories.get_deal(conn, deal_id)
    if not deal:
        await _send_html(update.effective_message, "⚠️ Deal not found.")
        return
    expectation = DepositExpectation(
        address=get_setting(conn, "usdt_trc20_deposit_address", ""),
        amount=deal.amount,
        memo=None,
        confirmations_required=get_int(conn, "confirmations_required_tron", 20),
        currency=deal.currency,
        network=deal.network,
    )
    if not expectation.address:
        await _send_html(update.effective_message, "⚠️ Deposit address not configured.")
        return
    try:
        response = await fetch_tron_transaction(tx_hash, get_setting(conn, "tron_api_url"))
    except Exception:  # noqa: BLE001
        await _send_html(update.effective_message, "⚠️ Could not reach TRON API.")
        return
    tx_data = response.get("data") or response
    valid, error = tron_usdt_matches(tx_data, expectation)
    if not valid:
        await _send_html(update.effective_message, f"⚠️ {error}")
        return
    user_ctx = _user_context(update, settings.admin_ids)
    payment = services.mark_funded(conn, user_ctx, deal_id, tx_hash=tx_hash)
    repositories.log_audit(conn, "trx" + utc_now(), user_ctx.user_id, "tron_verified", deal_id, db.json_dump({"confirmations": expectation.confirmations_required}), utc_now())
    await _send_html(update.effective_message, f"✅ Deposit verified. Tx: <code>{payment.tx_hash}</code>.")
    log_event(
        context.bot,
        conn,
        settings.admin_ids,
        "Deal Funded",
        "deal_funded",
        _deal_to_dict(repositories.get_deal(conn, deal_id)),
        {"buyer": repositories.get_username(conn, deal.buyer_id), "seller": repositories.get_username(conn, deal.seller_id), "tx_hash": tx_hash},
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data["settings"]
    user_ctx = _user_context(update, settings.admin_ids)
    if not user_ctx.is_admin:
        await _send_html(update.message, _admin_only_text())
        return
    await _send_html(update.message, "<b>🧑‍⚖️ Admin Panel</b>", _admin_panel_keyboard())


def _admin_panel_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [("📄 Deals", "admin_deals"), ("⚖️ Disputes", "admin_disputes")],
        [("💸 Fees", "admin_fees"), ("📏 Limits", "admin_limits")],
        [("📢 Logs", "admin_logs"), ("🔧 Config", "admin_config")],
        [("⏸ Pause", "admin_pause"), ("▶️ Resume", "admin_resume")],
        [("🏠 Menu", "menu_home")],
    ]
    return _build_keyboard(rows)


async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    user_ctx = _user_context(update, settings.admin_ids)
    if not user_ctx.is_admin:
        await _send_html(query.message, _admin_only_text())
        return
    if query.data == "admin_pause":
        toggle_setting(conn, "maintenance_mode", True)
        await _send_html(query.message, "Maintenance mode enabled.", _admin_panel_keyboard())
        return
    if query.data == "admin_resume":
        set_setting(conn, "maintenance_mode", "false")
        await _send_html(query.message, "Maintenance mode disabled.", _admin_panel_keyboard())
        return
    if query.data == "admin_fees":
        await _send_html(query.message, _admin_fees_text(conn), _admin_fees_keyboard())
        return
    if query.data == "admin_limits":
        await _send_html(query.message, _admin_limits_text(conn), _admin_limits_keyboard())
        return
    if query.data == "admin_logs":
        await _send_html(query.message, _admin_logs_text(conn), _admin_logs_keyboard(conn))
        return
    if query.data == "admin_config":
        await _send_html(query.message, _admin_config_text(conn), _admin_config_keyboard(conn))
        return
    if query.data == "admin_home":
        await _send_html(query.message, "<b>🧑‍⚖️ Admin Panel</b>", _admin_panel_keyboard())
        return
    if query.data == "admin_deals":
        await _send_html(query.message, "<b>📄 Deals</b>\n\nUse /confirmdeal <id> or /adminrelease <id>.", _admin_panel_keyboard())
        return
    if query.data == "admin_disputes":
        await _send_html(query.message, "<b>⚖️ Disputes</b>\n\nUse /admindispute <id> <resolution>.", _admin_panel_keyboard())
        return
    if query.data.startswith("toggle:"):
        key = query.data.split(":")[1]
        if key == "public_masking_mode":
            current = get_setting(conn, "public_masking_mode", "masked")
            set_setting(conn, "public_masking_mode", "extra" if current == "masked" else "masked")
        else:
            toggle_setting(conn, key, False)
        await _send_html(query.message, _admin_config_text(conn), _admin_config_keyboard(conn))
        return
    if query.data.startswith("set:"):
        key = query.data.split(":")[1]
        context.user_data["admin_edit"] = key
        await _send_html(query.message, f"<b>Enter value for {key}:</b>", _build_keyboard([[ ("❌ Cancel", "admin_config") ]]))
        return
    if query.data == "admin_log_test_private":
        log_event(
            context.bot,
            conn,
            settings.admin_ids,
            "Test Log",
            "admin_actions",
            {"id": "TEST", "status": "CONFIRMED", "amount": 0, "currency": "TON", "network": "TON", "title": "Test"},
            {"buyer": "test", "seller": "test"},
        )
        await _send_html(query.message, "Test log sent (if enabled).", _admin_logs_keyboard(conn))
        return
    if query.data == "admin_log_test_public":
        log_event(
            context.bot,
            conn,
            settings.admin_ids,
            "Test Log",
            "admin_actions",
            {"id": "TEST", "status": "CONFIRMED", "amount": 0, "currency": "TON", "network": "TON", "title": "Test"},
            {"buyer": "test", "seller": "test"},
        )
        await _send_html(query.message, "Test log sent (if enabled).", _admin_logs_keyboard(conn))
        return


async def admin_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    conn = context.bot_data["db"]
    key = context.user_data.get("admin_edit")
    if not key:
        return ConversationHandler.END
    value = update.message.text.strip()
    set_setting(conn, key, value)
    context.user_data.pop("admin_edit", None)
    await _send_html(update.message, f"Saved {key}.", _admin_panel_keyboard())
    return ConversationHandler.END


def _admin_fees_text(conn) -> str:
    fee_percent = get_float(conn, "fee_percent", 1.0)
    fee_flat = get_float(conn, "fee_flat", 0.0)
    return (
        "<b>💸 Fees</b>\n\n"
        f"• Percent: <b>{ui_text._format_percent(fee_percent)}%</b>\n"
        f"• Flat: <b>{fee_flat}</b>\n"
        f"• Wallet TON: {_wallet_mask(get_setting(conn, 'fee_wallet_ton'))}\n"
        f"• Wallet USDT-TON: {_wallet_mask(get_setting(conn, 'fee_wallet_usdt_ton'))}\n"
        f"• Wallet USDT-TRC20: {_wallet_mask(get_setting(conn, 'fee_wallet_usdt_trc20'))}"
    )


def _admin_fees_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [("Edit fee_percent", "set:fee_percent"), ("Edit fee_flat", "set:fee_flat")],
        [("Edit fee_wallet_ton", "set:fee_wallet_ton")],
        [("Edit fee_wallet_usdt_ton", "set:fee_wallet_usdt_ton")],
        [("Edit fee_wallet_usdt_trc20", "set:fee_wallet_usdt_trc20")],
        [("⬅️ Back", "admin_config"), ("🏠 Menu", "menu_home")],
    ]
    return _build_keyboard(rows)


def _admin_limits_text(conn) -> str:
    return (
        "<b>📏 Limits</b>\n\n"
        f"• Max amount: <b>{get_float(conn, 'max_deal_amount', 10000)}</b>\n"
        f"• Max active deals: <b>{get_int(conn, 'max_active_deals_per_user', 5)}</b>\n"
        f"• Rate limit seconds: <b>{get_int(conn, 'rate_limit_seconds', 60)}</b>"
    )


def _admin_limits_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [("Edit max_deal_amount", "set:max_deal_amount")],
        [("Edit max_active_deals_per_user", "set:max_active_deals_per_user")],
        [("Edit rate_limit_seconds", "set:rate_limit_seconds")],
        [("⬅️ Back", "admin_config"), ("🏠 Menu", "menu_home")],
    ]
    return _build_keyboard(rows)


def _admin_logs_text(conn) -> str:
    return (
        "<b>📢 Logs</b>\n\n"
        f"• Private channel: {get_setting(conn, 'private_log_channel_id') or '—'}\n"
        f"• Public channel: {get_setting(conn, 'public_log_channel_id') or '—'}\n"
    )


def _admin_logs_keyboard(conn) -> InlineKeyboardMarkup:
    rows = [
        [("Toggle private logs", "toggle:logs_private_enabled")],
        [("Toggle public logs", "toggle:logs_public_enabled")],
        [("Send Test Private Log", "admin_log_test_private")],
        [("Send Test Public Log", "admin_log_test_public")],
        [("Edit private_log_channel_id", "set:private_log_channel_id")],
        [("Edit public_log_channel_id", "set:public_log_channel_id")],
        [("⬅️ Back", "admin_config"), ("🏠 Menu", "menu_home")],
    ]
    return _build_keyboard(rows)


def _admin_config_text(conn) -> str:
    return (
        "<b>🔧 Config</b>\n\n"
        f"• Maintenance: {get_setting(conn, 'maintenance_mode', 'false')}\n"
        f"• Private logs: {get_setting(conn, 'logs_private_enabled', 'false')}\n"
        f"• Public logs: {get_setting(conn, 'logs_public_enabled', 'false')}\n"
        f"• Masking: {get_setting(conn, 'public_masking_mode', 'masked')}"
    )


def _admin_config_keyboard(conn) -> InlineKeyboardMarkup:
    rows = [
        [("Toggle maintenance", "toggle:maintenance_mode")],
        [("Toggle private logs", "toggle:logs_private_enabled")],
        [("Toggle public logs", "toggle:logs_public_enabled")],
        [("Toggle masking mode", "toggle:public_masking_mode")],
        [("Toggle log created", "toggle:log_event_deal_created")],
        [("Toggle log confirmed", "toggle:log_event_deal_confirmed")],
        [("Toggle log funded", "toggle:log_event_deal_funded")],
        [("Toggle log delivered", "toggle:log_event_deal_delivered")],
        [("Toggle log released", "toggle:log_event_deal_released")],
        [("Toggle log disputed", "toggle:log_event_deal_disputed")],
        [("Toggle log admin", "toggle:log_event_admin_actions")],
        [("Edit updates_channel_url", "set:updates_channel_url")],
        [("Edit vouches_channel_url", "set:vouches_channel_url")],
        [("Edit support_username_or_url", "set:support_username_or_url")],
        [("Edit ton_deposit_address", "set:ton_deposit_address")],
        [("Edit usdt_ton_deposit_address", "set:usdt_ton_deposit_address")],
        [("Edit usdt_trc20_deposit_address", "set:usdt_trc20_deposit_address")],
        [("Edit confirmations_required_ton", "set:confirmations_required_ton")],
        [("Edit confirmations_required_tron", "set:confirmations_required_tron")],
        [("⬅️ Back", "admin_home"), ("🏠 Menu", "menu_home")],
    ]
    return _build_keyboard(rows)


def _deposit_address(conn, currency: str, network: str) -> str:
    if currency == "TON" and network == "TON":
        return get_setting(conn, "ton_deposit_address", "")
    if currency == "USDT" and network == "TON":
        return get_setting(conn, "usdt_ton_deposit_address", "")
    if currency == "USDT" and network == "TRON":
        return get_setting(conn, "usdt_trc20_deposit_address", "")
    return ""


async def _send_deposit_instructions(message, conn, deal, back_callback: str = "menu_mydeals") -> None:
    address = _deposit_address(conn, deal.currency, deal.network)
    if not address:
        await _send_html(message, "⚠️ Deposit address not configured. Contact admin.", _back_menu_keyboard(back_callback))
        return
    memo = format_ton_memo(deal.id) if deal.network == "TON" else "N/A"
    text = (
        f"<b>💳 Deposit Instructions</b>\n\n"
        f"• Amount: <b>{deal.amount} {deal.currency}</b>\n"
        f"• Network: <b>{deal.network}</b>\n"
        f"• Address: <code>{address}</code>\n"
        f"• Memo/Comment: <code>{memo}</code>\n\n"
        "⚠️ Wrong network or missing memo = loss."
    )
    await _send_html(message, text, _back_menu_keyboard(back_callback))


def _fee_wallet(conn, currency: str, network: str) -> str:
    if currency == "TON" and network == "TON":
        return get_setting(conn, "fee_wallet_ton", "")
    if currency == "USDT" and network == "TON":
        return get_setting(conn, "fee_wallet_usdt_ton", "")
    if currency == "USDT" and network == "TRON":
        return get_setting(conn, "fee_wallet_usdt_trc20", "")
    return ""


def _lookup_user_id_by_username(conn, username: str) -> int | None:
    row = db.fetch_one(conn, "SELECT id FROM users WHERE username=?", (username,))
    return row["id"] if row else None


async def poll_ton_deposits(context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["db"]
    settings = context.bot_data["settings"]
    api_url = get_setting(conn, "ton_api_url", settings.ton_api_url)
    api_key = get_setting(conn, "ton_api_key", settings.ton_api_key)
    confirmations_required = get_int(conn, "confirmations_required_ton", 3)
    deals = repositories.list_confirmed_deals_for_network(conn, "TON", "TON")
    deals += repositories.list_confirmed_deals_for_network(conn, "USDT", "TON")

    for deal in deals:
        address = _deposit_address(conn, deal.currency, deal.network)
        if not address:
            continue
        memo = format_ton_memo(deal.id)
        expectation = DepositExpectation(
            address=address,
            amount=deal.amount,
            memo=memo,
            confirmations_required=confirmations_required,
            currency=deal.currency,
            network=deal.network,
        )
        try:
            payload = await fetch_ton_transactions(address, api_url, api_key=api_key)
        except Exception:  # noqa: BLE001
            continue
        for tx in parse_ton_transactions(payload):
            normalized = {
                "to": tx.get("to") or tx.get("in_msg", {}).get("destination"),
                "message": tx.get("message") or tx.get("in_msg", {}).get("message"),
                "value": tx.get("value") or tx.get("in_msg", {}).get("value"),
                "confirmations": tx.get("confirmations", 0),
                "hash": tx.get("transaction_id") or tx.get("hash"),
            }
            if ton_tx_matches(normalized, expectation):
                user_ctx = services.UserContext(user_id=settings.admin_ids[0] if settings.admin_ids else 0, username=None, is_admin=True)
                payment = services.mark_funded(conn, user_ctx, deal.id, tx_hash=normalized.get("hash"))
                repositories.log_audit(conn, "ton" + utc_now(), user_ctx.user_id, "ton_detected", deal.id, db.json_dump({"confirmations": normalized.get("confirmations", 0)}), utc_now())
                log_event(
                    context.bot,
                    conn,
                    settings.admin_ids,
                    "Deal Funded",
                    "deal_funded",
                    _deal_to_dict(repositories.get_deal(conn, deal.id)),
                    {"buyer": repositories.get_username(conn, deal.buyer_id), "seller": repositories.get_username(conn, deal.seller_id), "tx_hash": payment.tx_hash},
                )
                break


def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error", exc_info=context.error)


def build_application() -> Application:
    settings = load_settings()
    setup_logging(settings.log_level)
    conn = db.connect(settings.database_path)
    db.init_db(conn)
    ensure_defaults(conn, _settings_defaults(settings))

    application = Application.builder().token(settings.bot_token).build()
    application.bot_data["db"] = conn
    application.bot_data["settings"] = settings

    conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_handler, pattern="^menu_"), CommandHandler("newdeal", newdeal_command)],
        states={
            ROLE: [CallbackQueryHandler(role_selected, pattern="^role_")],
            COUNTERPARTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, counterparty_received)],
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title_received)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_received)],
            PROOF: [CallbackQueryHandler(proof_selected, pattern="^(proof_toggle:|proof_continue|proof_back)")],
            CURRENCY: [CallbackQueryHandler(currency_selected, pattern="^(currency_|currency_back)")],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_received)],
            CONFIRM: [CallbackQueryHandler(confirm_deal, pattern="^(confirm_deal|cancel_deal)$")],
        },
        fallbacks=[CommandHandler("menu", start)],
    )

    action_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(deal_callback, pattern="^deal_(submit_tx|mark_delivered|dispute|resolve):")],
        states={
            ACTION_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pending_action_input)],
        },
        fallbacks=[CommandHandler("menu", start)],
    )

    admin_edit_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_callbacks, pattern="^set:")],
        states={
            ADMIN_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_input)],
        },
        fallbacks=[CommandHandler("admin", admin_panel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("mydeals", mydeals_command))
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("deliver", deliver_command))
    application.add_handler(CommandHandler("release", release_command))
    application.add_handler(CommandHandler("dispute", dispute_command))
    application.add_handler(CommandHandler("submittx", submit_tx_command))
    application.add_handler(CommandHandler("mockdeposit", mockdeposit_command))
    application.add_handler(conversation)
    application.add_handler(action_conversation)
    application.add_handler(admin_edit_conversation)
    application.add_handler(CommandHandler("confirmdeal", confirm_deal_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(menu_handler, pattern="^menu_"))
    application.add_handler(CallbackQueryHandler(deal_callback, pattern="^deal_"))
    application.add_handler(CallbackQueryHandler(confirm_action_callback, pattern="^confirm_action:"))
    application.add_handler(CallbackQueryHandler(admin_callbacks, pattern="^admin_|^toggle:"))
    application.add_error_handler(error_handler)

    application.job_queue.run_repeating(poll_ton_deposits, interval=30, first=5)

    return application


def main() -> None:
    application = build_application()
    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
