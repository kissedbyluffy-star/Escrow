from __future__ import annotations

from typing import Iterable

from escrow_bot.constants import PROOF_TYPES

STATUS_EMOJIS = {
    "DRAFT": "🟡",
    "CONFIRMED": "🔵",
    "FUNDED": "💰",
    "DELIVERED": "📦",
    "RELEASED": "✅",
    "DISPUTED": "⚖️",
    "CLOSED": "🔒",
}

STATUS_LABELS = {
    "DRAFT": "Draft",
    "CONFIRMED": "Confirmed",
    "FUNDED": "Funded",
    "DELIVERED": "Delivered",
    "RELEASED": "Released",
    "DISPUTED": "Disputed",
    "CLOSED": "Closed",
}


def status_emoji(status: str) -> str:
    return STATUS_EMOJIS.get(status, "")


def status_text(status: str) -> str:
    return STATUS_LABELS.get(status, status.title())


def _format_percent(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def main_menu_text(fee_percent: float) -> str:
    return (
        "<b>🔒 Escrow</b> <i>— safe deals on Telegram</i>\n\n"
        "✅ TON • USDT (TON) • USDT (TRC20)\n"
        "🛡 Disputes handled by admin\n"
        f"💸 Fee: <b>{_format_percent(fee_percent)}%</b> (shown before you confirm)\n\n"
        "⚠️ Wrong network = funds lost forever\n"
        "<b>Rule:</b> If it’s not written, it doesn’t exist.\n\n"
        "Choose what you wanna do 👇"
    )


def menu_buttons() -> list[list[tuple[str, str]]]:
    return [
        [("🧾 New Deal", "menu_newdeal"), ("📂 My Deals", "menu_mydeals")],
        [("💳 Deposit Help", "menu_deposit_help"), ("💸 Fees", "menu_fees")],
        [("📢 Updates", "menu_updates"), ("✅ Vouches", "menu_vouches")],
        [("🧠 How It Works", "menu_how"), ("📜 Terms", "menu_terms")],
        [("🆘 Support", "menu_support")],
    ]


def back_menu_buttons(back_callback: str) -> list[list[tuple[str, str]]]:
    return [[("⬅️ Back", back_callback), ("🏠 Menu", "menu_home")]]


def info_not_configured() -> str:
    return "⚠️ Not configured by admin yet."


def updates_text(url: str | None) -> str:
    if not url:
        return info_not_configured()
    return "<b>📢 Updates</b>\n\nOfficial updates live here."


def vouches_text(url: str | None) -> str:
    if not url:
        return info_not_configured()
    return "<b>✅ Vouches</b>\n\nRecent vouches and completed deals."


def deposit_help_text() -> str:
    return (
        "<b>💳 Deposit Help</b>\n\n"
        "• Pick correct network (TON / USDT-TON / USDT-TRC20)\n"
        "• Wrong network = permanent loss\n"
        "• Check amount + address + memo (TON)"
    )


def fees_text(fee_percent: float, fee_flat: float, wallet_info: str) -> str:
    return (
        "<b>💸 Fees</b>\n\n"
        f"• Percent: <b>{_format_percent(fee_percent)}%</b>\n"
        f"• Flat: <b>{fee_flat}</b>\n"
        f"• Wallets: {wallet_info}"
    )


def how_text() -> str:
    return (
        "<b>🧠 How It Works</b>\n\n"
        "• Create a deal with clear terms\n"
        "• Both parties confirm\n"
        "• Buyer deposits\n"
        "• Seller delivers proof\n"
        "• Buyer releases or disputes\n"
        "• Admin executes payout"
    )


def terms_text() -> str:
    return (
        "<b>📜 Terms</b>\n\n"
        "• Escrow facilitator only\n"
        "• Admin resolves disputes\n"
        "• No private keys, no auto-withdrawals\n"
        "• If it’s not written, it doesn’t exist"
    )


def support_text(value: str | None) -> str:
    if not value:
        return "⚠️ Support contact not configured by admin yet."
    return f"<b>🆘 Support</b>\n\nReach us at: {value}"


def render_deal_list(deals: Iterable[dict]) -> str:
    lines = ["<b>📂 Your Deals</b>"]
    for deal in deals:
        lines.append(f"{status_emoji(deal['status'])} <code>{deal['id']}</code> — {deal['title']}")
    return "\n".join(lines)


def render_deal_details(
    deal: dict,
    buyer_username: str | None,
    seller_username: str | None,
    show_full_terms: bool,
    description_limit: int = 240,
) -> str:
    description = deal["description"]
    if not show_full_terms and len(description) > description_limit:
        description = description[: description_limit].rstrip() + "…"
    deadline = deal["deadline"] or "—"
    proof_list = "\n".join(f"• {item}" for item in deal["proof_types"])
    return (
        f"<b>🧾 Deal</b> <code>{deal['id']}</code>\n"
        f"<b>Status:</b> {status_emoji(deal['status'])} {status_text(deal['status'])}\n\n"
        f"• <b>Title:</b> {deal['title']}\n"
        f"• <b>Amount:</b> {deal['amount']} {deal['currency']}\n"
        f"• <b>Network:</b> {deal['network']}\n"
        f"• <b>Buyer:</b> @{buyer_username or 'unknown'}\n"
        f"• <b>Seller:</b> @{seller_username or 'unknown'}\n"
        f"• <b>Deadline:</b> {deadline}\n\n"
        f"<b>📌 Terms</b>\n{description}\n\n"
        f"<b>🧪 Proof</b>\n{proof_list}\n\n"
        "⚠️ Disputes use <b>Terms + Proof</b> only."
    )


def proof_toggle_label(index: int, selected: bool) -> str:
    label = PROOF_TYPES[index]
    prefix = "✅" if selected else "⬜"
    return f"{prefix} {label}"
