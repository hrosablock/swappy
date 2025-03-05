import logging

import aiohttp
from eth_utils import to_checksum_address
from web3 import AsyncWeb3

from bot.config import (approval_contract_addresses, chain_id_to_rpc_url,
                        evm_native_coin, gas_ratio)
from bot.utils.dex import (decrypt_key, get_aggregator_request_url,
                           get_headers_params, send_approve_tx, get_transaction_count)


async def get_swap_data(session, req_body, headers):
    url = get_aggregator_request_url("/swap", req_body)
    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            error_text = await response.text()
            logging.error(f"Request failed with status {response.status}: {error_text}")
            raise Exception(f"Request failed with status {response.status}")
        return await response.json()


async def swap(encrypted_key: str, chain_id: int, amount: str, from_token: str, to_token: str, wallet_address: str, price_impact_percent: int = 10, slippage_percent : int = 1):
    try:
        price_impact = str(round(price_impact_percent/100, 3))
        slippage = str(round(slippage_percent/100, 3))

        from_token = to_checksum_address(from_token)
        to_token = to_checksum_address(to_token)
        wallet_address = to_checksum_address(wallet_address)

        private_key = decrypt_key(encrypted_key)
        rpc_url = chain_id_to_rpc_url.get(chain_id)
        spender_address = approval_contract_addresses.get(chain_id)
        if not rpc_url or not spender_address:
            raise ValueError(f"Unsupported chain ID: {chain_id}")

        web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        if not await web3.is_connected():
            raise ConnectionError()

        req_body = {
            "chainId": str(chain_id),
            "amount": amount,
            "fromTokenAddress": from_token,
            "toTokenAddress": to_token,
            "slippage": slippage,
            "userWalletAddress": wallet_address,
            "priceImpactProtectionPercentage": price_impact
        }

        async with aiohttp.ClientSession() as session:
            if from_token.lower() != evm_native_coin.lower():
                approve_res = await send_approve_tx(session, web3, wallet_address, spender_address, from_token, amount, private_key, rpc_url, chain_id)
                nonce = await get_transaction_count(wallet_address, "pending", rpc_url, web3)
                approve_nonce = approve_res.get("nonce")

                if approve_res.get("ok") and nonce <= approve_nonce:
                    nonce = approve_nonce + 1
            else:
                nonce = await get_transaction_count(wallet_address, "pending", rpc_url, web3)

            headers = get_headers_params("GET", "aggregator", "/swap", req_body)
            swap_data = await get_swap_data(session, req_body, headers)
            swap_tx_info = swap_data["data"][0]["tx"]
            tx_object = {
                "data": swap_tx_info["data"],
                "gas": int(int(swap_tx_info["gas"]) * gas_ratio),
                "gasPrice": int(int(swap_tx_info["gasPrice"]) * gas_ratio),
                "to": swap_tx_info["to"],
                "value": int(swap_tx_info["value"]),
                "nonce": nonce,
                "chainId": chain_id
            }

            signed_tx = web3.eth.account.sign_transaction(tx_object, private_key)
            tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return web3.to_hex(tx_hash)
    except Exception:
        logging.exception("Error occurred in swap function")
        raise