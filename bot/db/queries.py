from aiogram import html
from sqlalchemy import update
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from bot.db.models import EVMLimitOrder, TONWallet, User, EVMWallet
from bot.utils.wallet_generator import evm_generator, ton_generator
from bot.utils.dex import decrypt_key, decrypt_mnemonic



async def get_user_by_id(db: AsyncSession, user_id: int):
    return (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()


async def get_user_by_id_for_update(db: AsyncSession, user_id: int):
    return (
        await db.execute(select(User).where(User.id == user_id).with_for_update())
    ).scalar_one_or_none()


async def user_referrals_update(db: AsyncSession, user: User) -> None:
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            referrals=user.referrals,
        )
    )


async def get_limit_order_by_hash(db: AsyncSession, user_id: int, hash: str):
    return (
        await db.execute(
            select(EVMLimitOrder)
            .where(EVMLimitOrder.user_id == user_id)
            .where(EVMLimitOrder.order_hash == hash)
        )
    ).scalar_one_or_none()


async def get_ton_wallet_by_id(db: AsyncSession, user_id: int):
    return (
        await db.execute(select(TONWallet).where(TONWallet.user_id == user_id))
    ).scalar_one_or_none()


async def registration(db: AsyncSession, user_id: int, message: Message, from_ref_id: int = None):
    if from_ref_id:
        referrer = await get_user_by_id_for_update(db, from_ref_id)
        if referrer and user_id not in referrer.referrals:
            referrer.referrals.append(user_id)
            await user_referrals_update(db, referrer)
        user = User.create_user(id=user_id, from_ref=from_ref_id)
        db.add(user)
    else:
        user = User.create_user(id=user_id, from_ref=None)
        db.add(user)
    
    enc_private_key, address = evm_generator()
    evm_wallet = EVMWallet.create_wallet(
        user_id=user_id, encrypted_private_key=enc_private_key, address=address
    )
    db.add(evm_wallet)
    
    enc_mnemonic, ton_address = await ton_generator()
    ton_wallet = TONWallet.create_wallet(
        user_id=user_id, encrypted_mnemonic=enc_mnemonic, address=ton_address
    )
    db.add(ton_wallet)
    
    await db.commit()
    user = await get_user_by_id(db, message.from_user.id)
    await message.answer(
        text=f"Your EVM private key: {html.spoiler(decrypt_key(enc_private_key))} and TON mnemonic: {html.spoiler(decrypt_mnemonic(enc_mnemonic))}"
    )
    return user