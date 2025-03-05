import logging
import re
import sys

from aiogram import F, Router, html
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from eth_utils.address import is_address
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import AsyncWeb3

from bot.config import (chain_id_to_name, chain_id_to_native_token_name,
                        chain_id_to_rpc_url, evm_native_coin, chain_id_to_tx_scan_url)
from bot.db.models import EVMSwap
from bot.db.queries import get_user_by_id
from bot.keyboards.menuKB import confirm_kb, cancel_kb, swap_from_token_kb, swap_chain_kb, menu_kb
from bot.trading.swap import swap
from bot.utils.balances import fetch_erc20_balances, get_balance
from bot.utils.token_details import get_token_decimals

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
router = Router()
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


class SwapState(StatesGroup):
    chain_id = State()
    from_token = State()
    to_token = State()
    amount = State()
    slippage_percent = State()
    price_impact_percent = State()
    confirm = State()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@router.callback_query(F.data == "swap")
async def start_swap(callback: CallbackQuery, state: FSMContext ) -> None:
    await state.set_state(SwapState.chain_id)
    await callback.message.answer(text="Let's swap!\nFirst, select a chain from the list:", reply_markup=swap_chain_kb())
    await callback.answer()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@router.callback_query(SwapState.chain_id, F.data.startswith("swap_chain_") & F.data.removeprefix("swap_chain_").isdigit())
async def set_chain_id(callback: CallbackQuery, db: AsyncSession, state: FSMContext):
    try:
        chain_id = int(callback.data.split("_")[2])
        chain_name = chain_id_to_name.get(chain_id, "")
        native_token_name = chain_id_to_native_token_name.get(chain_id)

        if not chain_name and not native_token_name:
            await callback.answer(f"Unsupported chain ID: {chain_id}")
            return
        user = await get_user_by_id(db, callback.from_user.id)

        if user:
            native_coin_balance = await get_balance(chain_id, user.evm_wallet.address, evm_native_coin)
            erc_balances_list, erc_balances_string = await fetch_erc20_balances(user.evm_wallet.address, chain_id)
            await callback.message.answer(
                text=f"Choose a token from the list or send its contract address:\n\n{native_token_name}: {round(native_coin_balance/(1e18), 10)}\n{html.code(evm_native_coin)}{erc_balances_string}",
                reply_markup=swap_from_token_kb(native_token_name, erc_balances_list)
            )
            await state.update_data(chain_id=chain_id)
            await state.set_state(SwapState.from_token)
        else:
            await callback.answer("User not found")
        await callback.answer()
    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@router.callback_query(SwapState.from_token, F.data.startswith("swap_from_token_"))
async def set_from_token(callback: CallbackQuery, state: FSMContext):
    try:
        from_token = callback.data.removeprefix("swap_from_token_")

        if is_address(from_token):
            await callback.message.answer(text=f"Now enter the receiving token's contract address:", reply_markup=cancel_kb())
            await state.update_data(from_token=from_token)
            await state.set_state(SwapState.to_token)
            await callback.answer()
        else:
            await callback.answer("Address is incorrect")
    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")



@router.message(SwapState.from_token)
async def set_from_token(message: Message, state: FSMContext):
    try:
        from_token = message.text

        if is_address(from_token):
            await message.answer(text=f"Now enter the receiving token's contract address:", reply_markup=cancel_kb())
            await state.update_data(from_token=from_token)
            await state.set_state(SwapState.to_token)
        else:
            await message.answer("Address is incorrect", reply_markup=cancel_kb())
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@router.message(SwapState.to_token)
async def set_to_token(message: Message, state: FSMContext):
    try:
        to_token = message.text

        if is_address(to_token):
            await message.answer(text=f"Now enter amount to swap:", reply_markup=cancel_kb())
            await state.update_data(to_token=to_token)
            await state.set_state(SwapState.amount)
        else:
            await message.answer("Address is incorrect", reply_markup=cancel_kb())
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@router.message(SwapState.amount, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_amount(message: Message, state: FSMContext, db: AsyncSession) -> None:
    try:
        amount = float(message.text.replace(",", "."))
        current_state = await state.get_data()
        user = await get_user_by_id(db, message.from_user.id)

        if user:
            current_balance = await get_balance(current_state.get("chain_id"), user.evm_wallet.address, current_state.get("from_token"))
            decimals = await get_token_decimals(current_state.get("chain_id"), current_state.get("from_token"))
            if current_balance < int(amount*(10**decimals)):
                await message.answer("Your balance doesn't match with your expectations", reply_markup=cancel_kb())
            else:
                await message.answer("Now enter the slippage % (0.1 to 10)", reply_markup=cancel_kb())
                await state.update_data(amount=int(amount*(10**decimals)))
                await state.set_state(SwapState.slippage_percent)
        else:
            await message.answer("User not found", reply_markup=cancel_kb())

    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@router.message(SwapState.slippage_percent, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_slippage_percent(message: Message, state: FSMContext) -> None:
    try:
        slippage = float(message.text.replace(",", "."))
        
        if 0.1 <= slippage <= 10:
            await message.answer("Now enter the price impact % (0.1 to 51)", reply_markup=cancel_kb())
            await state.update_data(slippage_percent=slippage)
            await state.set_state(SwapState.price_impact_percent)
        else:
            await message.answer("Invalid slippage percentage. Enter a value between 0.1 and 10", reply_markup=cancel_kb())
    
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")



@router.message(SwapState.price_impact_percent, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_price_impact_percent(message: Message, state: FSMContext) -> None:
    try:
        price_impact = float(message.text.replace(",", "."))
        
        if 0.1 <= price_impact <= 51:
            await message.answer("Confirm the swap:", reply_markup=confirm_kb())
            await state.update_data(price_impact_percent=price_impact)
            await state.set_state(SwapState.confirm)
        else:
            await message.answer("Invalid price impact percentage. Enter a value between 0.1 and 51", reply_markup=cancel_kb())
    
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@router.callback_query(SwapState.confirm, F.data == "confirm")
async def confirm_swap(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    try:
        user = await get_user_by_id(db, callback.from_user.id)
        if user:
            swap_data = await state.get_data()
            tx_hash = await swap(encrypted_key=user.evm_wallet.encrypted_private_key, chain_id=swap_data.get("chain_id"), amount=swap_data.get("amount"), from_token=swap_data.get("from_token"), to_token=swap_data.get("to_token"), wallet_address=user.evm_wallet.address, price_impact_percent=swap_data.get("price_impact_percent"), slippage_percent=swap_data.get("slippage_percent"))
            if tx_hash:
                await callback.message.answer(f"Swap tx initiated\n{html.code(tx_hash)}\n\n{chain_id_to_tx_scan_url.get(swap_data.get('chain_id'))}{tx_hash}", reply_markup=menu_kb())
                db.add(EVMSwap.create_swap(user_id=callback.from_user.id, chain_id=swap_data.get("chain_id"), amount=swap_data.get("amount"), from_token=swap_data.get("from_token"), to_token=swap_data.get("to_token"), tx_hash=tx_hash))
                await db.commit()
            else:
                await callback.answer("Swap failure")
        else:
            await callback.answer("User not found")
    except Exception as e:
        await callback.answer("Swap failure")
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
    finally:
        await state.clear()