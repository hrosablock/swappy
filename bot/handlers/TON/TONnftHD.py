import logging
import re
import sys

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.queries import get_user_by_id, registration
from bot.keyboards.menuKB import cancel_kb, confirm_kb, menu_kb
from bot.trading.TON.ton_nft import buy_nft
from bot.utils.balances import get_ton_balance
from bot.utils.token_details import ton_address_validation

router = Router()


class TON_NftState(StatesGroup):
    collection = State()
    to_price = State()
    confirm = State()


@router.callback_query(F.data == "ton_nft")
async def start_nft_purchase(
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
        await callback.message.answer(
            text=f"Send NFT collection contract address:\n\nYour TON balance: {formatted_balance}",
            reply_markup=cancel_kb(),
        )
        await state.set_state(TON_NftState.collection)
    else:
        await callback.message.answer("User not found", reply_markup=cancel_kb())
    await callback.answer()


@router.message(TON_NftState.collection, F.text)
async def set_collection(message: Message, state: FSMContext):
    if not ton_address_validation(message.text):
        await message.answer("Invalid collection address.", reply_markup=cancel_kb())
        return

    await state.update_data(collection=message.text)
    await message.answer(
        "Now enter the maximum price you are willing to pay for the NFT:",
        reply_markup=cancel_kb(),
    )
    await state.set_state(TON_NftState.to_price)


@router.message(TON_NftState.to_price, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_price(message: Message, state: FSMContext, db: AsyncSession):
    try:
        price = float(message.text.replace(",", "."))
        if price <= 0:
            await message.answer("Price can't be 0 or less", reply_markup=cancel_kb())
            return

        user = await get_user_by_id(db, message.from_user.id) or await registration(db, message.from_user.id, message)
        if not user:
            await message.answer("User not found", reply_markup=cancel_kb())
            return

        ton_balance = await get_ton_balance(
            user.ton_wallet.address, user.ton_wallet.encrypted_mnemonic
        )
        if (
            not ton_balance.get("ok")
            or float(ton_balance.get("balance") / 10**9) < price + 0.6
        ):
            await message.answer(
                "Insufficient balance.(add 0.6 TON for chain fees)",
                reply_markup=cancel_kb(),
            )
            return

        await state.update_data(to_price=price)
        await message.answer("Confirm purchase:", reply_markup=confirm_kb())
        await state.set_state(TON_NftState.confirm)
    except Exception as e:
        await message.answer("Invalid price format.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.callback_query(TON_NftState.confirm, F.data == "confirm")
async def confirm_purchase(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession
) -> None:
    try:
        user = await get_user_by_id(db, callback.from_user.id) or await registration(db, callback.from_user.id, callback.message)
        if not user:
            await callback.answer("User not found")
            return

        nft_data = await state.get_data()
        tx_hash = await buy_nft(
            encrypted_mnemonic=user.ton_wallet.encrypted_mnemonic,
            collection=nft_data.get("collection"),
            to_price=nft_data.get("to_price"),
        )

        if tx_hash:
            await callback.message.answer(
                f"NFT purchase initiated\nhttps://tonviewer.com/transaction/{tx_hash}",
                reply_markup=menu_kb(),
            )
        else:
            await callback.answer("Purchase failed")
    except Exception as e:
        await callback.answer("Purchase failed")
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
    finally:
        await state.clear()
