import logging
import re
import sys

from aiogram import F, Router, html
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from eth_utils.address import is_address
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import (chain_id_to_native_token_name, chain_id_to_tx_scan_url,
                        evm_native_coin)
from bot.db.queries import get_user_by_id
from bot.keyboards.menuKB import (cancel_kb, confirm_kb, menu_kb,
                                  withdraw_chain_kb, withdraw_token_kb)
from bot.trading.withdraw import send
from bot.utils.balances import fetch_erc20_balances, get_balance
from bot.utils.token_details import get_token_decimals

router = Router()

class WithdrawState(StatesGroup):
    chain_id = State()
    token_address = State()
    amount = State()
    recipient = State()
    confirm = State()


@router.callback_query(F.data == "withdraw")
async def start_withdraw(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(WithdrawState.chain_id)
    await callback.message.answer(text="Let's withdraw!\nFirst, select a chain from the list:", reply_markup=withdraw_chain_kb())
    await callback.answer()



@router.callback_query(WithdrawState.chain_id, F.data.startswith("withdraw_chain_") & F.data.removeprefix("withdraw_chain_").isdigit())
async def set_chain_id(callback: CallbackQuery, db: AsyncSession, state: FSMContext):
    try:
        chain_id = int(callback.data.split("_")[2])
        native_token_name = chain_id_to_native_token_name.get(chain_id)

        if not native_token_name:
            await callback.answer(f"Unsupported chain ID: {chain_id}")
            return
        
        user = await get_user_by_id(db, callback.from_user.id)
        if not user:
            await callback.answer("User not found.")
            return

        user_wallet = user.evm_wallet.address
        erc_balances_list, erc_balances_string = await fetch_erc20_balances(user_wallet, chain_id)
        native_balance = await get_balance(chain_id, user_wallet, evm_native_coin)
        formatted_balance = f"{round(native_balance / 1e18, 12):.12f}"

        await callback.message.answer(
            text=f"Choose a token to withdraw or send its contract address:\n\n{native_token_name}: {formatted_balance}\n{html.code(evm_native_coin)}\n{erc_balances_string}",
            reply_markup=withdraw_token_kb(native_token_name, erc_balances_list)
        )

        await state.update_data(chain_id=chain_id)
        await state.set_state(WithdrawState.token_address)

    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.callback_query(WithdrawState.token_address, F.data.startswith("withdraw_token_"))
async def set_token_address(callback: CallbackQuery, state: FSMContext):
    try:
        token_address = callback.data.removeprefix("withdraw_token_")

        if is_address(token_address):
            await callback.message.answer(text="Now enter the amount you want to withdraw:", reply_markup=cancel_kb())
            await state.update_data(token_address=token_address)
            await state.set_state(WithdrawState.amount)
        else:
            await callback.answer("Invalid token address.")

    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")



@router.message(WithdrawState.token_address)
async def set_token_address(message: Message, state: FSMContext):
    try:
        token_address = message.text

        if is_address(token_address):
            await message.answer(text="Now enter the amount you want to withdraw:", reply_markup=cancel_kb())
            await state.update_data(token_address=token_address)
            await state.set_state(WithdrawState.amount)
        else:
            await message.answer("Invalid token address.")
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")




@router.message(WithdrawState.amount, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_amount(message: Message, state: FSMContext, db: AsyncSession):
    try:
        amount = float(message.text.replace(",", "."))

        current_state = await state.get_data()
        chain_id = current_state.get("chain_id")
        token_address = current_state.get("token_address")
        user = await get_user_by_id(db, message.from_user.id)
        user_wallet = user.evm_wallet.address
        decimals = await get_token_decimals(chain_id, token_address)

        balance = await get_balance(chain_id, user_wallet, token_address)
        if balance < int(amount*(10**decimals)):
            await message.answer("Your balance is insufficient for this withdrawal.", reply_markup=cancel_kb())
            return

        await message.answer(f"Now enter recipient's address", reply_markup=cancel_kb())
        await state.update_data(amount=int(amount*(10**decimals)))
        await state.set_state(WithdrawState.recipient)
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.message(WithdrawState.recipient)
async def set_recipient_address(message: Message, state: FSMContext):
    try:
        recipient = message.text

        if is_address(recipient):
            await message.answer(text="Confirm withdrawal", reply_markup=confirm_kb())
            await state.update_data(recipient=recipient)
            await state.set_state(WithdrawState.confirm)
        else:
            await message.answer("Invalid token address.", reply_markup=cancel_kb())
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")





@router.callback_query(WithdrawState.confirm, F.data == "confirm")
async def confirm_withdraw(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    try:
        current_state = await state.get_data()
        chain_id = current_state.get("chain_id")
        token_address = current_state.get("token_address")
        amount = current_state.get("amount")
        user = await get_user_by_id(db, callback.from_user.id)
        encrypted_key = user.evm_wallet.encrypted_private_key
        to_wallet = current_state.get("recipient")

        tx_hash = await send(
            encrypted_key=encrypted_key, 
            chain_id=chain_id,
            amount=amount,
            token_address=token_address,
            to_wallet=to_wallet
        )

        if tx_hash:
            await callback.message.answer(f"Withdrawal initiated. Transaction hash: {html.code(tx_hash)}\n\n{chain_id_to_tx_scan_url.get(chain_id)}{tx_hash}", reply_markup=menu_kb())
        else:
            await callback.message.answer("Withdrawal failed.", reply_markup=menu_kb())
    except Exception as e:
        await callback.message.answer("Something went wrong during withdrawal.", reply_markup=menu_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
    finally:
        await state.clear()
