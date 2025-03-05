import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, DateTime,
                        ForeignKey, Index, Numeric, String, func, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from bot.db.enums import ChainID


class Base(AsyncAttrs, DeclarativeBase):
    pass


# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True, autoincrement=False)
    from_ref: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True, default=None)
    referrals: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


    evm_wallet: Mapped["EVMWallet"] = relationship("EVMWallet", back_populates="user", uselist=False, lazy="joined")
    evm_swaps: Mapped["EVMSwap"] = relationship("EVMSwap", back_populates="user", lazy="selectin")
    evm_limit_orders: Mapped["EVMLimitOrder"] = relationship("EVMLimitOrder", back_populates="user", lazy="selectin")
    evm_crosschain_swaps: Mapped["EvmCrosschainSwap"] = relationship("EvmCrosschainSwap", back_populates="user", lazy="selectin")

    __table_args__ = (
        CheckConstraint("id >= 0", name="check_user_id_non_negative"),
    )

    @staticmethod
    def create_user(id: int, from_ref: Optional[int] = None) -> "User":
        return User(id=id, from_ref=from_ref)


# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


class EVMWallet(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)
    encrypted_private_key: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)

    user = relationship("User", back_populates="evm_wallet", lazy="joined")

    __table_args__ = (
        CheckConstraint("user_id >= 0", name="check_wallet_user_id_non_negative"),
    )

    @staticmethod
    def create_wallet(user_id: int, encrypted_private_key: str, address: str) -> "EVMWallet":
        return EVMWallet(user_id=user_id, encrypted_private_key=encrypted_private_key, address=address)


# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


class EVMSwap(Base):
    __tablename__ = "evm_swaps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    chain_id: Mapped[ChainID] = mapped_column(nullable=False)
    amount: Mapped[Numeric] = mapped_column(Numeric(precision=100, scale=0), nullable=False)
    from_token: Mapped[str] = mapped_column(String, nullable=False)
    to_token: Mapped[str] = mapped_column(String, nullable=False)
    tx_hash: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="evm_swaps", lazy="selectin")

    __table_args__ = (
        CheckConstraint("user_id >= 0", name="check_swap_user_id_non_negative"),
        CheckConstraint("amount >= 0.0", name="check_swap_amount_non_negative"),
    )

    @staticmethod
    def create_swap(user_id: int, chain_id: ChainID, amount: int, from_token: str, to_token: str, tx_hash: str) -> "EVMSwap":
        return EVMSwap(user_id=user_id, chain_id=chain_id, amount=amount, from_token=from_token, to_token=to_token, tx_hash=tx_hash)


# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class EVMLimitOrder(Base):
    __tablename__ = "evm_limit_orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    chain_id: Mapped[ChainID] = mapped_column(nullable=False)
    salt: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    maker_token: Mapped[str] = mapped_column(String, nullable=False)
    taker_token: Mapped[str] = mapped_column(String, nullable=False)
    maker: Mapped[str] = mapped_column(String, nullable=False)
    allowed_sender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    making_amount: Mapped[Numeric] = mapped_column(Numeric(precision=100, scale=0), nullable=False)
    taking_amount: Mapped[Numeric] = mapped_column(Numeric(precision=100, scale=0), nullable=False)
    min_return: Mapped[Numeric] = mapped_column(Numeric(precision=100, scale=0), nullable=False)
    deadline: Mapped[int] = mapped_column(BigInteger, nullable=False)
    partially_able: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_hash: Mapped[str] = mapped_column(String, nullable=False)
    cancel_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="evm_limit_orders", lazy="selectin")

    canceled: Mapped[bool] = mapped_column(default=False, nullable=False)

    __table_args__ = (
        CheckConstraint("making_amount >= 0.0", name="check_making_amount_non_negative"),
        CheckConstraint("taking_amount >= 0.0", name="check_taking_amount_non_negative"),
        CheckConstraint("min_return >= 0.0", name="check_min_return_non_negative"),
        CheckConstraint("deadline > 0", name="check_deadline_positive"),
    )

    @staticmethod
    def create_limit(
        chain_id: int,
        user_id: int,
        salt: int,
        maker_token: str,
        taker_token: str,
        maker: str,
        allowed_sender: Optional[str],
        making_amount: float,
        taking_amount: float,
        min_return: float,
        deadline: int,
        partially_able: bool,
        order_hash : str
    ) -> "EVMLimitOrder":
        return EVMLimitOrder(
            chain_id=chain_id,
            user_id=user_id,
            salt=salt,
            maker_token=maker_token,
            taker_token=taker_token,
            maker=maker,
            allowed_sender=allowed_sender,
            making_amount=making_amount,
            taking_amount=taking_amount,
            min_return=min_return,
            deadline=deadline,
            partially_able=partially_able,
            order_hash=order_hash
        )


# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


class EvmCrosschainSwap(Base):
    __tablename__ = "evm_crosschain_swaps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    from_chain_id: Mapped[ChainID] = mapped_column(nullable=False)
    to_chain_id: Mapped[ChainID] = mapped_column(nullable=False)
    from_token: Mapped[str] = mapped_column(String, nullable=False)
    to_token: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Numeric] = mapped_column(Numeric(precision=100, scale=0), nullable=False)
    slippage: Mapped[Numeric] = mapped_column(Numeric(precision=5, scale=3), nullable=False)
    max_price_impact_percent: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_wallet: Mapped[str] = mapped_column(String, nullable=False)
    bridge_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tx_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="evm_crosschain_swaps", lazy="selectin")

    __table_args__ = (
        CheckConstraint("amount >= 0.0", name="check_swap_amount_non_negative"),
        CheckConstraint("max_price_impact_percent >= 0", name="check_price_impact_non_negative"),
    )

    @staticmethod
    def create_swap(
        user_id: int, from_chain_id: ChainID, to_chain_id: ChainID, from_token: str,
        to_token: str, amount: float, slippage: float, max_price_impact_percent: int,
        user_wallet: str, bridge_id: Optional[str] = None, tx_hash: Optional[str] = None
    ) -> "EvmCrosschainSwap":
        return EvmCrosschainSwap(
            user_id=user_id,
            from_chain_id=from_chain_id,
            to_chain_id=to_chain_id,
            from_token=from_token,
            to_token=to_token,
            amount=amount,
            slippage=slippage,
            max_price_impact_percent=max_price_impact_percent,
            user_wallet=user_wallet,
            bridge_id=bridge_id,
            tx_hash=tx_hash,
        )