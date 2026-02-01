from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from escrow_bot.ui import icons


def menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{icons.MENU['NEW_DEAL']} New Deal", callback_data="menu:new_deal"
                ),
                InlineKeyboardButton(
                    f"{icons.MENU['MY_DEALS']} My Deals", callback_data="menu:my_deals"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{icons.MENU['DEPOSIT_HELP']} Deposit Help", callback_data="info:deposit"
                ),
                InlineKeyboardButton(
                    f"{icons.MENU['FEES']} Fees", callback_data="info:fees"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{icons.MENU['UPDATES']} Updates", callback_data="info:updates"
                ),
                InlineKeyboardButton(
                    f"{icons.MENU['VOUCHES']} Vouches", callback_data="info:vouches"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{icons.MENU['HOW_IT_WORKS']} How It Works",
                    callback_data="info:how",
                ),
                InlineKeyboardButton(
                    f"{icons.MENU['TERMS']} Terms", callback_data="info:terms"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{icons.MENU['SUPPORT']} Support", callback_data="info:support"
                )
            ],
        ]
    )


def back_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{icons.DEAL_ACTIONS['BACK']} Back", callback_data="nav:back"
                ),
                InlineKeyboardButton(
                    f"{icons.DEAL_ACTIONS['MENU']} Menu", callback_data="nav:menu"
                ),
            ]
        ]
    )


def terms_accept_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ I Agree", callback_data="terms:accept"),
                InlineKeyboardButton("❌ Exit", callback_data="terms:exit"),
            ]
        ]
    )


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{icons.ADMIN['DEALS']} Deals", callback_data="admin:deals"
                ),
                InlineKeyboardButton(
                    f"{icons.ADMIN['DISPUTES']} Disputes", callback_data="admin:disputes"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{icons.ADMIN['FEES']} Fees", callback_data="admin:fees"
                ),
                InlineKeyboardButton(
                    f"{icons.ADMIN['LIMITS']} Limits", callback_data="admin:limits"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{icons.ADMIN['LOGS']} Logs", callback_data="admin:logs"
                ),
                InlineKeyboardButton(
                    f"{icons.ADMIN['CONFIG']} Config", callback_data="admin:config"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{icons.ADMIN['PAYOUTS']} Payouts", callback_data="admin:payouts"
                ),
                InlineKeyboardButton(
                    f"{icons.ADMIN['GROUPS']} Groups", callback_data="admin:groups"
                ),
            ],
            [
                InlineKeyboardButton(
                    "⏸ Maintenance", callback_data="admin:maintenance"
                ),
                InlineKeyboardButton(
                    f"{icons.ADMIN['PAUSE']} Pause Payouts",
                    callback_data="admin:pause_payouts",
                ),
            ],
        ]
    )
