import logging
import re
import sys
from html import escape as htmlescape

from aiogram import F, Router, html
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import bot_name
from bot.db.models import EVMWallet, TONWallet, User
from bot.db.queries import (
    get_ton_wallet_by_id,
    get_user_by_id,
    get_user_by_id_for_update,
    user_referrals_update,
)
from bot.keyboards.evmKB import evm_menu_kb
from bot.keyboards.menuKB import main_menu_kb, menu_kb
from bot.keyboards.tonKB import ton_menu_kb
from bot.utils.balances import fetch_jetton_balances
from bot.utils.dex import decrypt_key, decrypt_mnemonic
from bot.utils.wallet_generator import evm_generator, ton_generator

router = Router()


@router.message(
    CommandStart(deep_link=True, magic=F.args.regexp(re.compile(r"id_(\d+)")))
)
async def ref_start_handler(
    message: Message, command: CommandObject, db: AsyncSession, state: FSMContext
) -> None:
    try:
        await state.clear()

        if command.args.split("_")[1].isnumeric():
            from_ref_id = int(command.args.split("_")[1])
        else:
            from_ref_id = None

        user_id = message.from_user.id
        user = await get_user_by_id(db, user_id)
        TON_wallet = await get_ton_wallet_by_id(db, user_id)

        if user is None:
            if from_ref_id:
                referrer = await get_user_by_id_for_update(db, from_ref_id)
                if referrer and user.id not in referrer.referrals:
                    referrer.referrals.append(user.id)
                    await user_referrals_update(db, referrer)

                user = User.create_user(id=user_id, from_ref=from_ref_id)
                db.add(user)
            else:
                user = User.create_user(id=user_id, from_ref=None)
                db.add(user)

            enc_private_key, address = evm_generator()
            first_evm_wallet = EVMWallet.create_wallet(
                user_id=user_id, encrypted_private_key=enc_private_key, address=address
            )

            enc_mnemonic, ton_address = await ton_generator()
            first_ton_wallet = TONWallet.create_wallet(
                user_id=user_id, encrypted_mnemonic=enc_mnemonic, address=ton_address
            )
            db.add(first_evm_wallet)
            db.add(first_ton_wallet)
            await db.commit()
            await message.answer(
                text=f"Your EVM private key: {html.spoiler(decrypt_key(enc_private_key))} and TON mnemonic: {html.spoiler(decrypt_mnemonic(enc_mnemonic))}"
            )
            user = await get_user_by_id(db, user_id)

        elif TON_wallet is None:
            enc_mnemonic, ton_address = await ton_generator()
            first_ton_wallet = TONWallet.create_wallet(
                user_id=user_id, encrypted_mnemonic=enc_mnemonic, address=ton_address
            )
            db.add(first_ton_wallet)
            await db.commit()
            await message.answer(
                text=f"Your TON mnemonic: {html.spoiler(decrypt_mnemonic(enc_mnemonic))}"
            )
            user = await get_user_by_id(db, user_id)
        await message.answer(
            text=f"Hello, {html.bold(htmlescape(message.from_user.full_name))} and welcome! \nYour EVM wallet address: {html.code(user.evm_wallet.address)}\n Your TON wallet address: {html.code(user.ton_wallet.address)}\n\n<b>Select an option:</b>",
            reply_markup=main_menu_kb(),
        )

    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}")


@router.message(CommandStart())
async def start_handler(message: Message, db: AsyncSession, state: FSMContext) -> None:
    try:
        await state.clear()

        user_id = message.from_user.id
        user = await get_user_by_id(db, user_id)
        TON_wallet = await get_ton_wallet_by_id(db, user_id)

        if not user:
            user = User(id=user_id, from_ref=None)
            db.add(user)
            enc_private_key, address = evm_generator()
            first_evm_wallet = EVMWallet.create_wallet(
                user_id=user_id, encrypted_private_key=enc_private_key, address=address
            )

            enc_mnemonic, ton_address = await ton_generator()
            first_ton_wallet = TONWallet.create_wallet(
                user_id=user_id, encrypted_mnemonic=enc_mnemonic, address=ton_address
            )

            db.add(first_evm_wallet)
            db.add(first_ton_wallet)

            await db.commit()
            await message.answer(
                text=f"Your EVM private key: {html.spoiler(decrypt_key(enc_private_key))} and TON mnemonic: {html.spoiler(decrypt_mnemonic(enc_mnemonic))}"
            )
            user = await get_user_by_id(db, user_id)

        elif TON_wallet is None:
            enc_mnemonic, ton_address = await ton_generator()
            first_ton_wallet = TONWallet.create_wallet(
                user_id=user_id, encrypted_mnemonic=enc_mnemonic, address=ton_address
            )
            db.add(first_ton_wallet)
            await db.commit()
            await message.answer(
                text=f"Your TON mnemonic: {html.spoiler(decrypt_mnemonic(enc_mnemonic))}"
            )
            user = await get_user_by_id(db, user_id)

        await message.answer(
            text=f"Hello, {html.bold(htmlescape(message.from_user.full_name))} and welcome! \nYour EVM wallet address: {html.code(user.evm_wallet.address)}\n Your TON wallet address: {html.code(user.ton_wallet.address)}\n\n<b>Select an option:</b>",
            reply_markup=main_menu_kb(),
        )
    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.callback_query(F.data == "cancel")
@router.callback_query(F.data == "menu")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.message.answer(
            text=f"Hello, {html.bold(htmlescape(callback.from_user.full_name))} and welcome! <b>Select an option:</b>",
            reply_markup=main_menu_kb(),
        )

    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.callback_query(F.data == "wallets_evm")
async def callback_wallets_evm(callback: CallbackQuery):
    try:
        await callback.message.answer(
            text="Select an option:",
            reply_markup=evm_menu_kb(),
        )
    except Exception:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}")


@router.callback_query(F.data == "wallets_ton")
async def callback_wallets_ton(callback: CallbackQuery, db: AsyncSession):
    try:
        user = await get_user_by_id(db, callback.from_user.id)
        if user:
            _, jetton_balances_string = await fetch_jetton_balances(
                user.evm_wallet.address
            )
            await callback.message.answer(
                f"Your TON wallet address: {html.code(user.ton_wallet.address)}\n{jetton_balances_string}\n\n{html.bold('Select an option:')}",
                reply_markup=ton_menu_kb(),
            )
        else:
            await callback.answer("User not found")
    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}")


@router.callback_query(F.data == "ref")
async def callback_referral(callback: CallbackQuery):
    try:
        referral_link = f"https://t.me/{bot_name}?start=id_{callback.from_user.id}"
        await callback.message.answer(
            text=f"Your referral link: <code>{referral_link}</code>",
            reply_markup=menu_kb(),
        )

    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}")


@router.callback_query(F.data == "wallet")
async def callback_wallet(callback: CallbackQuery, db: AsyncSession):
    try:
        user_id = callback.from_user.id
        user = await get_user_by_id(db, user_id)

        if user:
            await callback.message.answer(
                f"Your EVM wallet address: {html.code(user.evm_wallet.address)}\n\nPrivate key: {html.spoiler(decrypt_key(user.evm_wallet.encrypted_private_key))}",
                reply_markup=main_menu_kb(),
            )
        else:
            await callback.answer("User not found")
    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}")


@router.callback_query(F.data == "ton_wallet")
async def callback_ton_wallet(callback: CallbackQuery, db: AsyncSession):
    try:
        user_id = callback.from_user.id
        user = await get_user_by_id(db, user_id)

        if user:
            await callback.message.answer(
                f"Your TON wallet address: {html.code(user.ton_wallet.address)}\n\n\nMnemonic: {html.spoiler(decrypt_mnemonic(user.ton_wallet.encrypted_mnemonic))}",
                reply_markup=main_menu_kb(),
            )
        else:
            await callback.answer("User not found")
    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}")
