import logging
import re
import sys
from html import escape as htmlescape

from aiogram import F, Router, html
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from eth_utils.address import is_address
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import chain_id_to_name, chain_id_to_tx_scan_url
from bot.db.queries import get_limit_order_by_hash, get_user_by_id
from bot.keyboards.menuKB import (cancel_kb, confirm_kb, limit_chain_kb,
                                  limit_from_token_kb, limit_yes_no_kb,
                                  menu_kb)
from bot.trading.limit import create_limit_order
from bot.utils.balances import fetch_erc20_balances, get_balance
from bot.utils.token_details import get_token_decimals

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
router = Router()
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class LimitOrderState(StatesGroup):
    chain_id = State()
    maker_token = State()
    taker_token = State()
    making_amount = State()
    taking_amount = State()
    min_return = State()
    deadline_hours = State()
    partially_able = State()
    confirm = State()

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@router.callback_query(F.data == "limit")
async def start_limit_order(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(LimitOrderState.chain_id)
    await callback.message.answer(text="Select a chain for your limit order:", reply_markup=limit_chain_kb())
    await callback.answer()


@router.callback_query(LimitOrderState.chain_id, F.data.startswith("limit_chain_"))
async def set_chain_id(callback: CallbackQuery, db: AsyncSession, state: FSMContext):
    try:
        chain_id = int(callback.data.split("_")[2])
        chain_name = chain_id_to_name.get(chain_id, "")

        if not chain_name:
            await callback.answer(f"Unsupported chain ID: {chain_id}")
            return
        user = await get_user_by_id(db, callback.from_user.id)

        if user:
            erc_balances_list, erc_balances_string = await fetch_erc20_balances(user.evm_wallet.address, chain_id)
            await callback.message.answer(
                text=f"Choose a token from the list or send its contract address:\n\n{erc_balances_string}",
                reply_markup=limit_from_token_kb(erc_balances_list)
            )
            await state.update_data(chain_id=chain_id)
            await state.set_state(LimitOrderState.maker_token)
        else:
            await callback.answer("User not found")

    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@router.callback_query(LimitOrderState.maker_token, F.data.startswith("limit_from_token_"))
async def set_maker_token(callback: CallbackQuery, state: FSMContext):
    try:
        maker_token = callback.data.removeprefix("limit_from_token_")
        print(maker_token)

        if is_address(maker_token):
            await callback.message.answer(text=f"Now enter the receiving token's contract address:", reply_markup=cancel_kb())
            await state.update_data(maker_token=maker_token)
            await state.set_state(LimitOrderState.taker_token)
    
        else:
            await callback.answer("Address is incorrect")
    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.message(LimitOrderState.maker_token)
async def set_maker_token(message: Message, state: FSMContext):
    try:
        maker_token = message.text

        if is_address(maker_token):
            await message.answer("Now enter the receiving token's contract address:", reply_markup=cancel_kb())
            await state.update_data(maker_token=maker_token)
            await state.set_state(LimitOrderState.taker_token)
        else:
            await message.answer("Invalid token address.", reply_markup=cancel_kb())
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.message(LimitOrderState.taker_token)
async def set_taker_token(message: Message, state: FSMContext):
    try:
        taker_token = message.text
        if is_address(taker_token):
            await message.answer("Enter the amount you want to sell:", reply_markup=cancel_kb())
            await state.update_data(taker_token=taker_token)
            await state.set_state(LimitOrderState.making_amount)
        else:
            await message.answer("Invalid token address.", reply_markup=cancel_kb())
    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")





@router.message(LimitOrderState.making_amount, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_making_amount(message: Message, state: FSMContext, db: AsyncSession):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            await message.answer("Amount can't be 0 or less", reply_markup=cancel_kb())
            return
        current_state = await state.get_data()
        user = await get_user_by_id(db, message.from_user.id)

        if user:
            current_balance = await get_balance(current_state.get("chain_id"), user.evm_wallet.address, current_state.get("maker_token"))
            decimals = await get_token_decimals(current_state.get("chain_id"), current_state.get("maker_token"))
            if current_balance < int(amount*(10**decimals)):
                await message.answer("Your balance doesn't match with your expectations", reply_markup=cancel_kb())
            else:
                await message.answer("Enter the amount of receiving token you want to get:", reply_markup=cancel_kb())
                await state.update_data(making_amount=int(amount*(10**decimals)))
                await state.set_state(LimitOrderState.taking_amount)
        else:
            await message.answer("User not found")

    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")




@router.message(LimitOrderState.taking_amount, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_taking_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            await message.answer("Amount can't be 0 or less", reply_markup=cancel_kb())
            return
        current_state = await state.get_data()

        decimals = await get_token_decimals(current_state.get("chain_id"), current_state.get("taker_token"))
        
        await message.answer("Now enter the minimum return amount of the swap:", reply_markup=cancel_kb())
        await state.update_data(taking_amount=int(amount*(10**decimals)))
        await state.set_state(LimitOrderState.min_return)

    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")




@router.message(LimitOrderState.min_return, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_min_return(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        current_state = await state.get_data()

        decimals = await get_token_decimals(current_state.get("chain_id"), current_state.get("taker_token"))
        
        if current_state.get("taking_amount") <= int(amount*(10**decimals)):
            await message.answer("It can't be greater or equal to taking amount", reply_markup=cancel_kb())
            return
        
        await message.answer("Now enter for how many hours the order will be active", reply_markup=cancel_kb())
        await state.update_data(min_return=int(amount*(10**decimals)))
        await state.set_state(LimitOrderState.deadline_hours)

    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")


@router.message(LimitOrderState.deadline_hours, F.text.regexp(re.compile(r"^\d+([.,]\d+)?$")))
async def set_deadline_hours(message: Message, state: FSMContext):
    try:
        hours = float(message.text.replace(",", "."))
        if hours > 1000 or hours < 0.016:
            await message.answer("The number must be less than 1000 and more than 0.016", reply_markup=cancel_kb())
            return
            
        await message.answer("Can order be partially filled?", reply_markup=limit_yes_no_kb())
        await state.update_data(deadline_hours=hours)
        await state.set_state(LimitOrderState.partially_able)

    except Exception as e:
        await message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")



@router.callback_query(LimitOrderState.partially_able, F.data.startswith("partially_"))
async def set_partially_able(callback: CallbackQuery, state: FSMContext):
    try:
        partially_able = True if callback.data.removeprefix("partially_") == 'yes' else False
        await callback.message.answer("Confirm the swap:", reply_markup=confirm_kb())
        await state.update_data(partially_able=partially_able)
        await state.set_state(LimitOrderState.confirm)

    except Exception as e:
        await callback.message.answer("Something went wrong.", reply_markup=cancel_kb())
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")



@router.callback_query(LimitOrderState.confirm, F.data == "confirm")
async def confirm_limit_order(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    try:
        user = await get_user_by_id(db, callback.from_user.id)
        if user:
            order_data = await state.get_data()
            order_hash = await create_limit_order(
                db=db,
                user_id=callback.from_user.id,
                encrypted_key=user.evm_wallet.encrypted_private_key,
                chain_id=order_data.get("chain_id"),
                user_wallet=user.evm_wallet.address,
                maker_token=order_data.get("maker_token"),
                taker_token=order_data.get("taker_token"),
                making_amount=order_data.get("making_amount"),
                taking_amount=order_data.get("taking_amount"),
                min_return=order_data.get("min_return"),
                deadline_hours=order_data.get("deadline_hours"),
                partially_able=order_data.get("partially_able"),
            )
            if order_hash:
                await callback.message.answer(f"Limit order created! Order hash: {html.code(order_hash)}", reply_markup=menu_kb())#\n Cancel: /cancel_limit {htmlescape('<order_hash>')}"
            else:
                await callback.answer("Limit order creation failed.")
        else:
            await callback.answer("User not found")
    except Exception as e:
        await callback.answer("Limit order creation failed.")
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
    finally:

        await state.clear()



# @router.message(Command('cancel_limit'))
# async def command_cancel_limit(message: Message, db: AsyncSession, command: CommandObject) -> None:
#     try:
#         userinput = command.args.split()
#         hash = userinput[0]

#         order = await get_limit_order_by_hash(db, message.from_user.id, hash)
#         user = await get_user_by_id(db, message.from_user.id)
#         if not user:
#             await message.answer("User not found")
#             return
#         if order is None:
#             await message.answer("Order not found")
#             return
        
#         order_data = {
#                     "salt": order.salt,
#                     "makerToken": order.maker_token,
#                     "takerToken": order.taker_token,
#                     "maker": order.maker,
#                     "receiver": order.maker,
#                     "allowedSender": order.allowed_sender,
#                     "makingAmount": order.making_amount,
#                     "takingAmount": order.taking_amount,
#                     "minReturn": order.min_return,
#                     "deadLine": order.deadline,
#                     "partiallyAble": order.partially_able
#                 }

#         tx_hash = await cancel_limit(order_data, user.evm_wallet.encrypted_private_key, user.evm_wallet.address, order.chain_id)

#         if tx_hash:
#             await message.answer(f"Cancel tx initiated\n{html.code(tx_hash)}\n\n{chain_id_to_tx_scan_url.get(order.chain_id)}{tx_hash}")
#         else:
#             await message.answer("Something went wrong.", reply_markup=cancel_kb())
#     except Exception as e:
#         await message.answer("Something went wrong.", reply_markup=cancel_kb())
#         logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")