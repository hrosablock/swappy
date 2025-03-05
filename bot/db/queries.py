from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from bot.db.models import (EVMLimitOrder, User)


async def get_user_by_id(db: AsyncSession, user_id: int):
    return (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def get_user_by_id_for_update(db: AsyncSession, user_id: int):
    return (await db.execute(select(User).where(User.id == user_id).with_for_update())).scalar_one_or_none()


async def user_referrals_update(db: AsyncSession, user: User) -> None:
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            referrals=user.referrals,
        )
    )


async def get_limit_order_by_hash(db: AsyncSession, user_id: int, hash: str):
    return (await db.execute(select(EVMLimitOrder).where(EVMLimitOrder.user_id == user_id).where(EVMLimitOrder.order_hash == hash))).scalar_one_or_none()