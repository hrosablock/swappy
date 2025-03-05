from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import chain_id_to_name, evm_native_coin, crosschain_approval_contract, limit_approval_contract

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


def main_menu_kb():
    buttons = [
        [InlineKeyboardButton(text="Wallet", callback_data="wallet"), InlineKeyboardButton(text="Swap", callback_data="swap")],
        [InlineKeyboardButton(text="Limit", callback_data="limit"), InlineKeyboardButton(text="Crosschain", callback_data="crosschain")],
        [InlineKeyboardButton(text="👥", callback_data="ref"), InlineKeyboardButton(text="Withdraw", callback_data="withdraw")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="cancel")]])

def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Menu", callback_data="menu")]])

def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Confirm", callback_data="confirm")], [InlineKeyboardButton(text="Cancel", callback_data="cancel")]])


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


def swap_chain_kb():
    buttons = [
        [InlineKeyboardButton(text=name.capitalize(), callback_data=f"swap_chain_{chain_id}")] for chain_id, name in chain_id_to_name.items()
    ]
    
    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def swap_from_token_kb(native_token_name: str, erc_balances_list: list, include_native: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    if include_native:
        buttons.append([InlineKeyboardButton(text=native_token_name, callback_data=f"swap_from_token_{evm_native_coin}")])
    erc_limit = 8 if include_native else 9
    buttons += [[InlineKeyboardButton(text=token["name"],  callback_data=f"swap_from_token_{token.get('token_address')}")]
                for token in erc_balances_list[:erc_limit]]
    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def withdraw_chain_kb():
    buttons = [
        [InlineKeyboardButton(text=name.capitalize(), callback_data=f"withdraw_chain_{chain_id}")]
        for chain_id, name in chain_id_to_name.items()
    ]
    
    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def withdraw_token_kb(native_token_name: str, erc_balances_list: list, include_native: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    if include_native:
        buttons.append([InlineKeyboardButton(text=native_token_name, 
                                            callback_data=f"withdraw_token_{evm_native_coin}")])
    erc_limit = 8 if include_native else 9
    buttons += [[InlineKeyboardButton(text=token["name"], 
                                      callback_data=f"withdraw_{token.get('token_address')}")]
                for token in erc_balances_list[:erc_limit]]
    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


def crosschain_from_chain_kb():
    common_chain_ids = set(chain_id_to_name.keys()) & set(crosschain_approval_contract.keys())
    
    buttons = [
        [InlineKeyboardButton(text=name.capitalize(), callback_data=f"crosschain_from_chain_{chain_id}")]
        for chain_id, name in chain_id_to_name.items() if chain_id in common_chain_ids
    ]
    
    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def crosschain_to_chain_kb():
    common_chain_ids = set(chain_id_to_name.keys()) & set(crosschain_approval_contract.keys())
    
    buttons = [
        [InlineKeyboardButton(text=name.capitalize(), callback_data=f"crosschain_to_chain_{chain_id}")]
        for chain_id, name in chain_id_to_name.items() if chain_id in common_chain_ids
    ]
    
    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def crosschain_token_kb(native_token_name: str, erc_balances_list: list, include_native: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    if include_native:
        buttons.append([InlineKeyboardButton(text=native_token_name, 
                                            callback_data=f"crosschain_token_{evm_native_coin}")])
    erc_limit = 8 if include_native else 9
    buttons += [[InlineKeyboardButton(text=token["name"], 
                                      callback_data=f"crosschain_token_{token.get('token_address')}")]
                for token in erc_balances_list[:erc_limit]]
    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def limit_chain_kb():
    common_chain_ids = set(chain_id_to_name.keys()) & set(limit_approval_contract.keys())
    
    buttons = [
        [InlineKeyboardButton(text=name.capitalize(), callback_data=f"limit_chain_{chain_id}")]
        for chain_id, name in chain_id_to_name.items() if chain_id in common_chain_ids
    ]
    
    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def limit_from_token_kb(erc_balances_list: list) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=token["name"], callback_data=f"limit_from_token_{token.get('token_address')}")] for token in erc_balances_list[:9]]

    buttons.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def limit_yes_no_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Yes", callback_data="partially_yes")], [InlineKeyboardButton(text="No", callback_data="partially_no")]])