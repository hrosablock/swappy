import asyncio
import json
import logging
import time

import aiohttp
from eth_utils import to_checksum_address
from web3 import AsyncWeb3

from bot.config import (
    ZERO_ADDRESS,
    api_base_url,
    cancel_limit_abi,
    chain_id_to_rpc_url,
    limit_approval_contract,
    limit_dex_router,
    limit_order_type,
)
from bot.db.models import EVMLimitOrder
from bot.utils.dex import decrypt_key, get_headers_params, send_approve_tx


async def sign_limit_order(
    web3: AsyncWeb3,
    private_key,
    chain_id,
    verifying_contract,
    salt,
    maker_token,
    taker_token,
    maker,
    making_amount,
    taking_amount,
    min_return,
    deadline,
    partially_able,
):
    try:
        full_message = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "Order": limit_order_type,
            },
            "primaryType": "Order",
            "domain": {
                "name": "OKX LIMIT ORDER",
                "version": "2.0",
                "chainId": chain_id,
                "verifyingContract": verifying_contract,
            },
            "message": {
                "salt": salt,
                "makerToken": maker_token,
                "takerToken": taker_token,
                "maker": maker,
                "receiver": maker,
                "allowedSender": ZERO_ADDRESS,
                "makingAmount": making_amount,
                "takingAmount": taking_amount,
                "minReturn": min_return,
                "deadLine": deadline,
                "partiallyAble": partially_able,
            },
        }
        signature = await asyncio.to_thread(
            web3.eth.account.sign_typed_data, private_key, full_message=full_message
        )
        return {
            "orderHash": signature.messageHash.hex(),
            "signature": signature.signature.hex(),
            "chainId": str(chain_id),
            "data": full_message.get("message"),
        }
    except Exception:
        logging.exception("Error occurred in send_limit_order function")
        raise


async def send_limit_order(session, limit_order_request_params: dict):
    url = f"{api_base_url}/aggregator/limit-order/save-order"
    headers = get_headers_params(
        "POST",
        "aggregator",
        "/limit-order/save-order",
        body=json.dumps(limit_order_request_params),
    )

    try:
        async with session.post(
            url, headers=headers, data=json.dumps(limit_order_request_params)
        ) as response:
            if response.status == 200:
                response_data = await response.json()
                if response_data.get("code") == "0":
                    return True
                else:
                    logging.error(f"Error response: {response_data}")
                    raise Exception(f"Error: {response_data}")
            else:
                response_text = await response.text()
                logging.error(
                    f"Request failed with status {response.status}: {response_text}"
                )
                raise Exception(f"Error {response.status}: {response_text}")
    except Exception:
        logging.exception("Error occurred in send_limit_order function")
        raise


async def create_limit_order(
    db,
    user_id,
    encrypted_key: str,
    chain_id: int,
    user_wallet: str,
    maker_token: str,
    taker_token: str,
    making_amount: int,
    taking_amount: int,
    min_return: int,
    deadline_hours: float,
    partially_able: bool,
):
    try:
        rpc_url = chain_id_to_rpc_url.get(chain_id)
        spender_address = limit_approval_contract.get(chain_id)
        verifying_contract = limit_dex_router.get(chain_id)

        if not rpc_url or not spender_address or not verifying_contract:
            raise ValueError(f"Unsupported chain ID: {chain_id}")

        web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        if not await web3.is_connected():
            raise ConnectionError()

        private_key = decrypt_key(encrypted_key)
        user_wallet = to_checksum_address(user_wallet)
        maker_token = to_checksum_address(maker_token)
        taker_token = to_checksum_address(taker_token)

        async with aiohttp.ClientSession() as session:
            await send_approve_tx(
                session,
                web3,
                user_wallet,
                spender_address,
                maker_token,
                making_amount,
                private_key,
                rpc_url,
                chain_id,
            )
            salt = int(time.time())
            deadline = int(int(time.time()) + int((deadline_hours * 3600)))

            signature_params = await sign_limit_order(
                web3=web3,
                private_key=private_key,
                chain_id=chain_id,
                verifying_contract=verifying_contract,
                salt=salt,
                maker_token=maker_token,
                taker_token=taker_token,
                maker=user_wallet,
                making_amount=making_amount,
                taking_amount=taking_amount,
                min_return=min_return,
                deadline=deadline,
                partially_able=partially_able,
            )

            if signature_params:
                res = await send_limit_order(
                    session, limit_order_request_params=signature_params
                )
                if res:
                    db.add(
                        EVMLimitOrder.create_limit(
                            chain_id=chain_id,
                            user_id=user_id,
                            salt=salt,
                            maker_token=maker_token,
                            taker_token=taker_token,
                            maker=user_wallet,
                            allowed_sender=ZERO_ADDRESS,
                            making_amount=making_amount,
                            taking_amount=taking_amount,
                            min_return=min_return,
                            deadline=deadline,
                            partially_able=partially_able,
                            order_hash=signature_params.get("orderHash"),
                        )
                    )
                    await db.commit()
                    return signature_params.get("orderHash")
        return False
    except Exception:
        logging.exception("Error occurred in create_limit_order function")
        raise


# async def cancel_limit(order_data: dict, encrypted_key: str, user_address, chain_id):
#     try:
#         rpc_url = chain_id_to_rpc_url.get(chain_id)

#         if not rpc_url:
#             raise ValueError(f"Unsupported chain ID: {chain_id}")

#         web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
#         if not await web3.is_connected():
#             raise ConnectionError()


#         private_key = decrypt_key(encrypted_key)
#         dex_router = limit_dex_router.get(chain_id)
#         user_address = to_checksum_address(user_address)
#         contract = web3.eth.contract(address=dex_router, abi=cancel_limit_abi)
#         nonce = await web3.eth.get_transaction_count(user_address)
#         tx_object = await contract.functions.cancelOrder(order_data).build_transaction({
#             "nonce": nonce,
#             "value": 0,
#             "chainId": chain_id,
#             "from": user_address
#         })
#         signed_tx = web3.eth.account.sign_transaction(tx_object, private_key)
#         tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
#         return tx_hash.hex()
#     except Exception:
#         logging.exception("Error occurred in cancel_limit function")
#         raise
