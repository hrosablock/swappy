import logging
import re
import sys

from aiogram import F, Router, html
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.queries import get_user_by_id, registration
from bot.keyboards.menuKB import cancel_kb, confirm_kb, menu_kb
from bot.keyboards.tonKB import ton_withdraw_token_kb
from bot.trading.TON.withdraw import send, send_jetton
from bot.utils.balances import fetch_jetton_balances, get_ton_balance
from bot.utils.token_details import get_jetton_decimals, ton_address_validation

router = Router()

ton_native_coin = "TON"


class TON_WithdrawState(StatesGroup):
    token = State()
    destination = State()
    amount = State()
    confirm = State()


@router.callback_query(F.data == "ton_withdraw")
async def start_withdraw(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    user = await get_user_by_id(db, callback.from_user.id) or await registration(db, callback.from_user.id, callback.message)

    if user:
        ton_balance = await get_ton_balance(
            user.ton_wallet.address, user.ton_wallet.encrypted_mnemonic
        )
        if not ton_balance.get("ok"):
            await callback.message.answer(
                ton_balance.get("message"), reply_markup=menu_kb()
            )
            return

        formatted_balance = float(ton_balance.get("balance") / 10**9)
        jetton_balances, jetton_balances_string = await fetch_jetton_balances(
            user.ton_wallet.address
        )
        await callback.message.answer(
            text=f"Let's withdraw!\nFirst, select a token from the list or send its contract address:\n\nTON: {formatted_balance}\n{jetton_balances_string}",
            reply_markup=ton_withdraw_token_kb(jetton_balances),
        )
        await state.set_state(TON_WithdrawState.token)
    else:
        await callback.message.answer("User not found", reply_markup=cancel_kb())
    await callback.answer()


@router.callback_query(TON_WithdrawState.token, F.data.startswith("TWT_"))
async def set_token(callback: CallbackQuery, state: FSMContext):
    try:
        token = callback.data.removeprefix("TWT_")

        if ton_address_validation(token) or token.upper() == ton_native_coin:
            await state.update_data(token=token)
            await callback.message.answer(
                "Now enter destination address:", reply_markup=cancel_kb()
            )
            await state.set_state(TON_WithdrawState.destination)
        else:
            await callback.answer("Invalid token address.", reply_markup=cancel_kb())
    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.message(TON_WithdrawState.token, F.text)
async def set_token(message: Message, state: FSMContext):
    token = message.text.strip()
    if ton_address_validation(token) or token.upper() == ton_native_coin:
        await state.update_data(token=token)
        await message.answer("Now enter destination address:", reply_markup=cancel_kb())
        await state.set_state(TON_WithdrawState.destination)
    else:
        await message.answer("Invalid token address.", reply_markup=cancel_kb())


@router.message(TON_WithdrawState.destination, F.text)
async def set_destination(message: Message, state: FSMContext):
    destination = message.text.strip()
    if ton_address_validation(destination):
        await state.update_data(destination=destination)
        await message.answer(
            "Now enter the amount to withdraw:", reply_markup=cancel_kb()
        )
        await state.set_state(TON_WithdrawState.amount)
    else:
        await message.answer("Invalid destination address.", reply_markup=cancel_kb())


@router.message(TON_WithdrawState.amount, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            await message.answer("Amount can't be 0 or less", reply_markup=cancel_kb())
            return

        await state.update_data(amount=amount)
        await message.answer("Confirm withdrawal:", reply_markup=confirm_kb())
        await state.set_state(TON_WithdrawState.confirm)
    except Exception as e:
        await message.answer("Invalid amount format.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.callback_query(TON_WithdrawState.confirm, F.data == "confirm")
async def confirm_withdraw(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    try:
        user = await get_user_by_id(db, callback.from_user.id) or await registration(db, callback.from_user.id, callback.message)

        withdraw_data = await state.get_data()
        token = withdraw_data.get("token")
        destination = withdraw_data.get("destination")
        amount = withdraw_data.get("amount")

        if token.upper() == ton_native_coin:
            tx_hash = await send(
                encrypted_mnemonic=user.ton_wallet.encrypted_mnemonic,
                destination=destination,
                amount=amount,
            )
        else:
            decimals = get_jetton_decimals(token)
            if decimals:
                tx_hash = await send_jetton(
                    encrypted_mnemonic=user.ton_wallet.encrypted_mnemonic,
                    destination=destination,
                    jetton_amount=amount,
                    jetton_master_address=token,
                    jetton_decimals=9,
                )
            else:
                await callback.answer("Error parsing token decimals")
                return

        if tx_hash:
            await callback.message.answer(
                f"Withdrawal initiated\nhttps://tonviewer.com/transaction/{tx_hash}",
                reply_markup=menu_kb(),
            )
        else:
            await callback.message.answer(
                f"Withdrawal failed. Please check your balance or try again later.",
                reply_markup=menu_kb(),
            )
    except Exception as e:
        await callback.message.answer(
            f"Withdrawal failed. Please check your balance or try again later.",
            reply_markup=menu_kb(),
        )
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
    finally:
        await state.clear()
