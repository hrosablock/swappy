from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import ton_native_coin


def ton_menu_kb():
    buttons = [
        [
            InlineKeyboardButton(text="Wallet", callback_data="ton_wallet"),
            InlineKeyboardButton(text="Swap", callback_data="ton_swap"),
        ],
        [
            InlineKeyboardButton(text="Nft", callback_data="ton_nft")
        ],
        [
            InlineKeyboardButton(text="Withdraw", callback_data="ton_withdraw"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def ton_swap_from_token_kb(jetton_balances_list: list) -> InlineKeyboardMarkup:
    buttons = [[
                InlineKeyboardButton(
                    text='TON',
                    callback_data=f"TSFT_{ton_native_coin}",
                )
            ]]
    
    buttons += [
        [
            InlineKeyboardButton(
                text=token["name"],
                callback_data=f"TSFT_{token.get('token_address')}",
            )
        ]
        for token in jetton_balances_list[:8]
    ]
    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def ton_withdraw_token_kb(jetton_balances_list: list) -> InlineKeyboardMarkup:
    buttons = [[
                InlineKeyboardButton(
                    text='TON',
                    callback_data=f"TWT_{ton_native_coin}",
                )
            ]]
    
    buttons += [
        [
            InlineKeyboardButton(
                text=token["name"],
                callback_data=f"TWT_{token.get('token_address')}",
            )
        ]
        for token in jetton_balances_list[:8]
    ]
    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)