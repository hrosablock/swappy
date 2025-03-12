import logging
import re
import sys

from aiogram import F, Router, html
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import ton_native_coin
from bot.db.models import TONSwap
from bot.db.queries import get_user_by_id, registration
from bot.keyboards.menuKB import cancel_kb, confirm_kb, menu_kb
from bot.keyboards.tonKB import ton_swap_from_token_kb
from bot.trading.TON.swap import jetton_to_jetton, jetton_to_ton, ton_to_jetton
from bot.utils.balances import (
    fetch_jetton_balances,
    get_jetton_balance,
    get_ton_balance,
)
from bot.utils.token_details import get_jetton_decimals, ton_address_validation

router = Router()


class TONSwapState(StatesGroup):
    from_token = State()
    to_token = State()
    amount = State()
    confirm = State()


@router.callback_query(F.data == "ton_swap")
async def start_swap(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    try:

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
                text=f"Let's swap!\nFirst, select a token from the list or send its contract address:\n\nTON: {formatted_balance}\n{jetton_balances_string}",
                reply_markup=ton_swap_from_token_kb(jetton_balances),
            )

            await state.set_state(TONSwapState.from_token)
        else:
            await callback.message.answer("User not found", reply_markup=cancel_kb())
    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.callback_query(TONSwapState.from_token, F.data.startswith("TSFT_"))
async def set_from_token(callback: CallbackQuery, state: FSMContext):
    try:
        from_token = callback.data.removeprefix("TSFT_")

        if ton_address_validation(from_token) or from_token.upper() == ton_native_coin:
            await callback.message.answer(
                text=f"Now enter the receiving token's contract address or send {html.code('TON')} for swap to TON:",
                reply_markup=cancel_kb(),
            )
            await state.update_data(from_token=from_token)
            await state.set_state(TONSwapState.to_token)
        else:
            await callback.answer("Address is incorrect")
    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.message(TONSwapState.from_token)
async def set_from_token(message: Message, state: FSMContext):
    try:
        from_token = message.text.strip()

        if ton_address_validation(from_token) or from_token.upper() == ton_native_coin:
            await message.answer(
                text=f"Now enter the receiving token's contract address or send {html.code('TON')} for swap to TON:",
                reply_markup=cancel_kb(),
            )
            await state.update_data(from_token=from_token)
            await state.set_state(TONSwapState.to_token)
        else:
            await message.answer("Address is incorrect")
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.message(TONSwapState.to_token)
async def set_to_token(message: Message, state: FSMContext):
    try:
        to_token = message.text.strip()

        if ton_address_validation(to_token) or to_token.upper() == ton_native_coin:
            await message.answer(
                text=f"Now enter amount to swap:", reply_markup=cancel_kb()
            )
            await state.update_data(to_token=to_token)
            await state.set_state(TONSwapState.amount)
        else:
            await message.answer("Address is incorrect", reply_markup=cancel_kb())
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.message(TONSwapState.amount, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_amount(message: Message, state: FSMContext, db: AsyncSession) -> None:
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            await message.answer("Amount can't be 0 or less", reply_markup=cancel_kb())
            return

        current_state = await state.get_data()
        user = await get_user_by_id(db, message.from_user.id) or await registration(db, message.from_user.id, message)

        if not user:
            await message.answer("User not found", reply_markup=cancel_kb())
            return

        from_token = current_state.get("from_token")
        if not from_token:
            await message.answer("Invalid token selection", reply_markup=cancel_kb())
            return

        if from_token.upper() == ton_native_coin:
            balance_data = await get_ton_balance(
                user.ton_wallet.address, user.ton_wallet.encrypted_mnemonic
            )
            if not balance_data.get("ok"):
                await message.answer(
                    balance_data.get("message"), reply_markup=menu_kb()
                )
                return
            current_balance = balance_data.get("balance", 0)
            decimals = 9
        elif ton_address_validation(from_token):
            current_balance = (
                await get_jetton_balance(user.ton_wallet.address, from_token) or 0
            )
            decimals = await get_jetton_decimals(from_token) or 9
        else:
            await message.answer("Address is incorrect", reply_markup=cancel_kb())
            return

        amount_scaled = int(amount * (10**decimals))

        if current_balance < amount_scaled:
            await message.answer(
                "Your balance doesn't match with your expectations",
                reply_markup=cancel_kb(),
            )
        else:
            await message.answer(
                "Now, confirm the swap",
                reply_markup=confirm_kb(),
            )
            await state.update_data(amount=amount_scaled)
            await state.set_state(TONSwapState.confirm)

    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.callback_query(TONSwapState.confirm, F.data == "confirm")
async def confirm_swap(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    try:
        user = await get_user_by_id(db, callback.from_user.id) or await registration(db, callback.from_user.id, callback.message)
        if user:
            swap_data = await state.get_data()
            if (
                swap_data.get("from_token").upper() != ton_native_coin
                and swap_data.get("to_token").upper() != ton_native_coin
            ):
                tx_hash = await jetton_to_jetton(
                    encrypted_mnemonic=user.ton_wallet.encrypted_mnemonic,
                    from_token=swap_data.get("from_token"),
                    to_token=swap_data.get("to_token"),
                    amount=swap_data.get("amount"),
                )
            elif swap_data.get("from_token").upper() == ton_native_coin:
                tx_hash = await ton_to_jetton(
                    encrypted_mnemonic=user.ton_wallet.encrypted_mnemonic,
                    token=swap_data.get("to_token"),
                    amount=swap_data.get("amount"),
                )
            elif swap_data.get("to_token").upper() == ton_native_coin:
                tx_hash = await jetton_to_ton(
                    encrypted_mnemonic=user.ton_wallet.encrypted_mnemonic,
                    token=swap_data.get("from_token"),
                    amount=swap_data.get("amount"),
                )
            else:
                await callback.answer("Unsupported swap")
                return
            if tx_hash:
                await callback.message.answer(
                    f"Swap tx initiated\nhttps://tonviewer.com/transaction/{tx_hash}",
                    reply_markup=menu_kb(),
                )
                db.add(
                    TONSwap.create_swap(
                        user_id=callback.from_user.id,
                        amount=swap_data.get("amount"),
                        from_token=swap_data.get("from_token"),
                        to_token=swap_data.get("to_token"),
                    )
                )
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
