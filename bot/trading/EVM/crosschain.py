import asyncio
import logging

import aiohttp
from eth_utils import to_checksum_address
from web3 import AsyncWeb3

from bot.config import (
    chain_id_to_rpc_url,
    crosschain_approval_contract,
    evm_native_coin,
    gas_ratio,
)
from bot.utils.dex import (
    decrypt_key,
    get_crosschain_request_url,
    get_headers_params,
    get_transaction_count,
    send_approve_tx,
)


async def get_supported_chain(from_chain_id: int, to_chain_id: int = None):
    try:
        params = {"chainId": str(from_chain_id)}
        url = get_crosschain_request_url("/supported/chain", params)
        headers = get_headers_params("GET", "cross-chain", "/supported/chain", params)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                if data.get("code") == "0" and "data" in data:
                    for chain in data["data"]:
                        if to_chain_id and int(chain["chainId"]) == to_chain_id:
                            return chain
        return None
    except Exception as e:
        logging.exception(f"Error in get_supported_chain: {e}")
        return None


async def get_quote_and_bridge_id(
    from_chain_id: int,
    to_chain_id: int,
    from_token: str,
    to_token: str,
    amount: str,
    slippage: float,
    max_price_impact: float,
):
    try:
        params = {
            "fromChainId": str(from_chain_id),
            "toChainId": str(to_chain_id),
            "fromTokenAddress": from_token,
            "toTokenAddress": to_token,
            "amount": amount,
            "slippage": str(slippage),
            "priceImpactProtectionPercentage": max_price_impact,
        }
        url = get_crosschain_request_url("/quote", params)
        headers = get_headers_params("GET", "cross-chain", "/quote", params)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                if data.get("code") == "0" and "data" in data and data["data"]:
                    bridge_id = (
                        data["data"][0]
                        .get("routerList", [{}])[0]
                        .get("router", {})
                        .get("bridgeId")
                    )
                    return {"ok": True, "bridge_id": bridge_id}
                return {"ok": False, "message": data.get("msg", "Unknown error")}
    except Exception as e:
        logging.exception(f"Error in get_quote_and_bridge_id: {e}")
        return {"ok": False, "message": "Unknown error"}


async def crosschain_swap(
    encrypted_key: str,
    from_chain_id: int,
    to_chain_id: int,
    amount: str,
    from_token: str,
    to_token: str,
    user_wallet: str,
    slippage_percent: float,
    max_price_impact_percent: float = 5.0,
):
    try:
        max_price_impact = round(max_price_impact_percent / 100, 3)
        slippage = round(slippage_percent / 100, 3)
        from_token = to_checksum_address(from_token)
        to_token = to_checksum_address(to_token)
        user_wallet = to_checksum_address(user_wallet)
        private_key = decrypt_key(encrypted_key)
        spender_address = crosschain_approval_contract.get(from_chain_id)
        rpc_url = chain_id_to_rpc_url.get(from_chain_id)
        if not rpc_url:
            raise ValueError(f"Unsupported chain ID: {from_chain_id}")
        web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        if not await web3.is_connected():
            raise ConnectionError("Web3 provider not connected")
        async with aiohttp.ClientSession() as session:
            if from_token.lower() != evm_native_coin.lower():
                approve_res = await send_approve_tx(
                    session,
                    web3,
                    user_wallet,
                    spender_address,
                    from_token,
                    amount,
                    private_key,
                    rpc_url,
                    from_chain_id,
                )
                nonce = await get_transaction_count(
                    user_wallet, "pending", rpc_url, web3
                )
                approve_nonce = approve_res.get("nonce")
                if approve_res.get("ok") and nonce <= approve_nonce:
                    nonce = approve_nonce + 1
            else:
                nonce = await get_transaction_count(
                    user_wallet, "pending", rpc_url, web3
                )
            quote_data = await get_quote_and_bridge_id(
                from_chain_id,
                to_chain_id,
                from_token,
                to_token,
                amount,
                slippage,
                max_price_impact,
            )
            if not quote_data.get("ok"):
                return quote_data
            bridge_id = quote_data.get("bridge_id")
            swap_params = {
                "fromChainId": str(from_chain_id),
                "toChainId": str(to_chain_id),
                "fromTokenAddress": from_token,
                "toTokenAddress": to_token,
                "amount": amount,
                "slippage": str(slippage),
                "userWalletAddress": user_wallet,
                "bridgeId": bridge_id,
            }
            headers = get_headers_params("GET", "cross-chain", "/build-tx", swap_params)
            url = get_crosschain_request_url("/build-tx", swap_params)
            async with session.get(url, headers=headers) as response:
                swap_data = await response.json()
                if swap_data.get("code") != "0" or not swap_data.get("data"):
                    return {
                        "ok": False,
                        "message": swap_data.get("msg", "Unknown error"),
                    }
            swap_tx_info = swap_data["data"][0]["tx"]
            tx_object = {
                "data": swap_tx_info["data"],
                "gas": int(int(swap_tx_info["gasLimit"]) * gas_ratio),
                "gasPrice": int(int(swap_tx_info["gasPrice"]) * gas_ratio),
                "to": swap_tx_info["to"],
                "value": int(swap_tx_info["value"]),
                "nonce": nonce,
                "chainId": from_chain_id,
            }
            signed_tx = web3.eth.account.sign_transaction(tx_object, private_key)
            tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            return {"ok": True, "tx_hash": web3.to_hex(tx_hash)}
    except Exception as e:
        logging.exception(f"Error in crosschain_swap: {e}")
        return {"ok": False, "message": "Error in crosschain_swap"}


async def check_transaction_status(transaction_tx: str):
    try:
        query_params = {"hash": transaction_tx}
        url = get_crosschain_request_url("/status", query_params)
        headers = get_headers_params("GET", "cross-chain", "/status", query_params)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception(f"Error in check_transaction_status: {e}")
        return None
