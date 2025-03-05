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
from bot.db.models import EvmCrosschainSwap
from bot.db.queries import get_user_by_id
from bot.keyboards.menuKB import confirm_kb, cancel_kb, crosschain_from_chain_kb, crosschain_to_chain_kb, crosschain_token_kb, menu_kb
from bot.trading.crosschain import crosschain_swap
from bot.utils.balances import fetch_erc20_balances, get_balance
from bot.utils.token_details import get_token_decimals


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
router = Router()
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


class CrosschainState(StatesGroup):
    from_chain = State()
    to_chain = State()
    from_token = State()
    to_token = State()
    amount = State()
    slippage_percent = State()
    price_impact_percent = State()
    confirm = State()


@router.callback_query(F.data == "crosschain")
async def start_crosschain_swap(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CrosschainState.from_chain)
    await callback.message.answer(text="Let's perform a crosschain swap!\nFirst, select the source chain:", reply_markup=crosschain_from_chain_kb())
    await callback.answer()



@router.callback_query(CrosschainState.from_chain, F.data.startswith("crosschain_from_chain_") & F.data.removeprefix("crosschain_from_chain_").isdigit())
async def set_from_chain(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        from_chain_id = int(callback.data.split("_")[3])
        chain_name = chain_id_to_name.get(from_chain_id)

        if not chain_name:
            await callback.answer(f"Unsupported chain ID: {from_chain_id}")
            return

        await callback.message.answer(text="Now, select the destination chain:", reply_markup=crosschain_to_chain_kb())
        await state.update_data(from_chain=from_chain_id)
        await state.set_state(CrosschainState.to_chain)
    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")

@router.callback_query(CrosschainState.to_chain, F.data.startswith("crosschain_to_chain_") & F.data.removeprefix("crosschain_to_chain_").isdigit())
async def set_to_chain(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    try:
        to_chain_id = int(callback.data.split("_")[3])

        current_state = await state.get_data()
        from_chain = current_state.get("from_chain")
        native_token_name = chain_id_to_native_token_name.get(from_chain)

        if not native_token_name:
            await callback.answer(f"Unsupported chain ID: {from_chain}")
            return
        user = await get_user_by_id(db, callback.from_user.id)

        if user:
            native_coin_balance = await get_balance(from_chain, user.evm_wallet.address, evm_native_coin)
            erc_balances_list, erc_balances_string = await fetch_erc20_balances(user.evm_wallet.address, from_chain)
            await callback.message.answer(text=f"Please provide the token address or select from available tokens:\n\n{native_token_name}: {round(native_coin_balance/(1e18), 10)}\n{html.code(evm_native_coin)}{erc_balances_string}", 
                                         reply_markup=crosschain_token_kb(native_token_name, erc_balances_list))
            await state.update_data(to_chain=to_chain_id)
            await state.set_state(CrosschainState.from_token)
        else:
            await callback.answer("User not found")

    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.callback_query(CrosschainState.from_token, F.data.startswith("crosschain_token_"))
async def set_from_token(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        from_token = callback.data.removeprefix("crosschain_token_")

        if is_address(from_token):
            await callback.message.answer(text=f"Now enter the receiving token's contract address in destination chain:", reply_markup=cancel_kb())
            await state.update_data(from_token=from_token)
            await state.set_state(CrosschainState.to_token)
    
        else:
            await callback.answer("Address is incorrect")
    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.message(CrosschainState.from_token)
async def set_from_token(message: Message, state: FSMContext):
    try:
        from_token = message.text

        if is_address(from_token):
            await message.answer(text=f"Now enter the receiving token's contract address in destination chain:", reply_markup=cancel_kb())
            await state.update_data(from_token=from_token)
            await state.set_state(CrosschainState.to_token)
        else:
            await message.answer("Address is incorrect", reply_markup=cancel_kb())
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")



@router.message(CrosschainState.to_token)
async def set_to_token(message: Message, state: FSMContext):
    try:
        to_token = message.text

        if is_address(to_token):
            await message.answer(text=f"Now enter amount to swap:", reply_markup=cancel_kb())
            await state.update_data(to_token=to_token)
            await state.set_state(CrosschainState.amount)
        else:
            await message.answer("Address is incorrect", reply_markup=cancel_kb())
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")



@router.message(CrosschainState.amount, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_amount(message: Message, state: FSMContext, db: AsyncSession) -> None:
    try:
        amount = float(message.text.replace(",", "."))
        current_state = await state.get_data()
        user = await get_user_by_id(db, message.from_user.id)

        if user:
            current_balance = await get_balance(current_state.get("from_chain"), user.evm_wallet.address, current_state.get("from_token"))
            decimals = await get_token_decimals(current_state.get("from_chain"), current_state.get("from_token"))
            if current_state.get("from_token").lower() == evm_native_coin.lower():
                rpc_url = chain_id_to_rpc_url.get(current_state.get("from_chain"))
                web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
                if not await web3.is_connected():
                    raise ConnectionError()
                gas_price = await web3.eth.gas_price 
                fee = (gas_price*150000)
                if current_balance-fee < int(amount*(10**decimals)):
                    await message.answer("Your balance doesn't match with your expectations", reply_markup=cancel_kb())
            elif current_balance < int(amount*(10**decimals)):
                await message.answer("Your balance doesn't match with your expectations", reply_markup=cancel_kb())
            else:
                await message.answer("Now enter the slippage % (0.1 to 10)", reply_markup=cancel_kb())
                await state.update_data(amount=int(amount*(10**decimals)))
                await state.set_state(CrosschainState.slippage_percent)
        else:
            await message.answer("User not found")

    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")



@router.message(CrosschainState.slippage_percent, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_slippage_percent(message: Message, state: FSMContext) -> None:
    try:
        slippage = float(message.text.replace(",", "."))
        
        if 0.1 <= slippage <= 10:
            await message.answer("Now enter the price impact % (0.1 to 51)", reply_markup=cancel_kb())
            await state.update_data(slippage_percent=slippage)
            await state.set_state(CrosschainState.price_impact_percent)
        else:
            await message.answer("Invalid slippage percentage. Enter a value between 0.1 and 10", reply_markup=cancel_kb())
    
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")





@router.message(CrosschainState.price_impact_percent, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_price_impact_percent(message: Message, state: FSMContext) -> None:
    try:
        price_impact = float(message.text.replace(",", "."))

        if 0.1 <= price_impact <= 51:
            await state.update_data(price_impact_percent=price_impact)
            await message.answer("Confirm the swap:", reply_markup=confirm_kb())
            await state.set_state(CrosschainState.confirm)
        else:
            await message.answer("Invalid price impact percentage. Please enter a value between 0.1 and 51", reply_markup=cancel_kb())

    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.callback_query(CrosschainState.confirm, F.data == "confirm")
async def confirm_crosschain_swap(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    try:
        user = await get_user_by_id(db, callback.from_user.id)
        if user:
            swap_data = await state.get_data()
            tx_hash = await crosschain_swap(
                encrypted_key=user.evm_wallet.encrypted_private_key,
                from_chain_id=swap_data["from_chain"],
                to_chain_id=swap_data["to_chain"],
                amount=str(swap_data["amount"]),
                from_token=swap_data["from_token"],
                to_token=swap_data["to_token"],
                user_wallet=user.evm_wallet.address,
                slippage_percent=swap_data["slippage_percent"],
                max_price_impact_percent=swap_data["price_impact_percent"]
            )

            if tx_hash["ok"]:
                db.add(EvmCrosschainSwap.create_swap(
                    user_id=user.id,
                    from_chain_id=swap_data["from_chain"],
                    to_chain_id=swap_data["to_chain"],
                    from_token=swap_data["from_token"],
                    to_token=swap_data["to_token"],
                    amount=swap_data["amount"],
                    slippage=swap_data["slippage_percent"],
                    max_price_impact_percent=swap_data["price_impact_percent"],
                    user_wallet=user.evm_wallet.address,
                    tx_hash=tx_hash["tx_hash"]
                ))
                await db.commit()
                await callback.message.answer(f"Crosschain swap initiated! Transaction hash: {html.code(tx_hash.get('tx_hash'))}\n\n{chain_id_to_tx_scan_url.get(swap_data.get('from_chain'))}{tx_hash.get('tx_hash')}", reply_markup=menu_kb())
            else:
                await callback.message.answer(f"Error: {tx_hash.get('message')}", reply_markup=menu_kb())

        else:
            await callback.answer("User not found")

    except Exception as e:
        await callback.answer("Crosschain swap failed")
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
    finally:

        await state.clear()