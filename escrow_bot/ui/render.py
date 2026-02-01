from __future__ import annotations

from escrow_bot.ui import icons, text


def render_home() -> str:
    return "\n\n".join([text.HOME_TITLE, text.HOME_BULLETS, text.HOME_WARNING, text.HOME_CTA])


def render_terms(terms_version: str) -> str:
    return f"{text.TERMS_TITLE}\n\n{text.TERMS_BODY}\n\n<b>Version:</b> <code>{terms_version}</code>"


def render_how_it_works() -> str:
    return f"{text.HOW_IT_WORKS_TITLE}\n\n{text.HOW_IT_WORKS_BODY}"


def render_fees(fee_percent: str, fee_flat: str) -> str:
    return f"{text.FEES_TITLE}\n\n{text.FEES_BODY}\n\n<b>Percent:</b> {fee_percent}%\n<b>Flat:</b> {fee_flat}"


def render_deal_list(deals: list[dict]) -> str:
    if not deals:
        return "<b>📂 My Deals</b>\n\nNo deals yet."
    rows = [
        f"{icons.STATUS[deal['status']]} <code>{deal['deal_id']}</code> — {deal['title']}"
        for deal in deals
    ]
    return "<b>📂 My Deals</b>\n\n" + "\n".join(rows)


def render_deal_detail(deal: dict) -> str:
    lines = [
        f"{icons.STATUS[deal['status']]} <b>Deal</b> <code>{deal['deal_id']}</code>",
        f"<b>Amount:</b> {deal['display_amount']} {deal['asset']}",
        f"<b>Network:</b> {deal['network']}",
        f"<b>Buyer:</b> {deal['buyer']}",
        f"<b>Seller:</b> {deal['seller']}",
    ]
    return "\n".join(lines)


def render_deposit_instructions(deal: dict, address: str, memo: str | None) -> str:
    memo_line = f"\n<b>Memo:</b> <code>{memo}</code>" if memo else ""
    return (
        f"{icons.DEAL_ACTIONS['DEPOSIT_INSTRUCTIONS']} <b>Deposit Instructions</b>\n"
        f"<b>Send:</b> {deal['display_amount']} {deal['asset']}\n"
        f"<b>To:</b> <code>{address}</code>{memo_line}\n"
        f"⚠️ Safety\n"
        f"• Wrong network = irreversible loss\n"
        f"• Exact amount required"
    )


def render_admin_dashboard() -> str:
    return text.ADMIN_TITLE


def render_log_private(message: str) -> str:
    return f"{text.LOG_PRIVATE_TITLE}\n\n{message}"


def render_log_public(message: str) -> str:
    return f"{text.LOG_PUBLIC_TITLE}\n\n{message}"
