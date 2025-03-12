from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb():
    buttons = [
        [InlineKeyboardButton(text="EVM wallet", callback_data="wallets_evm")],
        [InlineKeyboardButton(text="TON wallet", callback_data="wallets_ton")],
        [InlineKeyboardButton(text="👥", callback_data="ref")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="cancel")]]
    )


def menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Menu", callback_data="menu")]]
    )


def confirm_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Confirm", callback_data="confirm")],
            [InlineKeyboardButton(text="Cancel", callback_data="cancel")],
        ]
    )
