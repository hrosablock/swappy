import base64
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import aiohttp
from cryptography.fernet import Fernet
from web3 import AsyncWeb3

from bot.config import allowance_abi, api_base_url, gas_ratio
from bot.env import (
    FERNET_KEY,
    OKX_API_KEY,
    OKX_PASSPHRASE,
    OKX_PROJECT_ID,
    OKX_SECRET_KEY,
)


async def get_transaction_count(
    user_address: str, block_type: str, rpc_url: str, web3: AsyncWeb3
):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionCount",
        "params": [user_address, block_type],
        "id": 1,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                rpc_url, json=payload, headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return int(result["result"], 16) if "result" in result else None
    except Exception:
        return await web3.eth.get_transaction_count(user_address, block_type)


def decrypt_key(key: str):
    try:
        return Fernet(FERNET_KEY).decrypt(key).hex()
    except Exception:
        logging.exception("Error decrypting key")
        raise


def decrypt_mnemonic(mnemonic: str):
    try:
        return Fernet(FERNET_KEY).decrypt(mnemonic).decode()
    except Exception:
        logging.exception("Error decrypting mnemonic")
        raise


def get_aggregator_request_url(method_name: str, query_params: dict):
    try:
        return f"{api_base_url}/aggregator{method_name}?{urlencode(query_params)}"
    except Exception:
        logging.exception("Error constructing aggregator request URL")
        raise


def get_crosschain_request_url(method_name: str, query_params: dict):
    try:
        return f"{api_base_url}/cross-chain{method_name}?{urlencode(query_params)}"
    except Exception:
        logging.exception("Error constructing crosschain request URL")
        raise


def get_headers_params(
    request_method: str,
    base_path: str,
    method_name: str,
    query_params: dict = None,
    body: dict = None,
):
    try:
        date = datetime.now(timezone.utc).isoformat()[:-9] + "Z"
        query_string = f"?{urlencode(query_params)}" if query_params else ""
        body = "" if body is None else body
        url = f"/api/v5/dex/{base_path}{method_name}{query_string}"
        message = f"{date}{request_method}{url}{body}"
        sign = base64.b64encode(
            hmac.new(OKX_SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
        ).decode()

        return {
            "Content-Type": "application/json",
            "OK-ACCESS-PROJECT": OKX_PROJECT_ID,
            "OK-ACCESS-KEY": OKX_API_KEY,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": date,
            "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
        }
    except Exception:
        logging.exception("Error constructing headers parameters")
        raise


async def get_allowance(
    web3: AsyncWeb3, owner_address: str, spender_address: str, token_address: str
):
    token_contract = web3.eth.contract(
        address=web3.to_checksum_address(token_address), abi=allowance_abi
    )
    try:
        return int(
            await token_contract.functions.allowance(
                owner_address, spender_address
            ).call()
        )
    except Exception:
        logging.exception("Error getting allowance")
        raise


async def approve_transaction(session, chain_id: int, from_token: str, amount: str):
    try:
        headers = get_headers_params(
            "GET",
            "aggregator",
            "/approve-transaction",
            {
                "chainId": str(chain_id),
                "tokenContractAddress": from_token,
                "approveAmount": amount,
            },
        )
        url = get_aggregator_request_url(
            "/approve-transaction",
            {
                "chainId": str(chain_id),
                "tokenContractAddress": from_token,
                "approveAmount": amount,
            },
        )

        async with session.get(url, headers=headers) as response:
            return await response.json()
    except Exception:
        logging.exception("Error approving transaction")
        raise


async def send_approve_tx(
    session,
    web3: AsyncWeb3,
    user: str,
    spender_address: str,
    from_token: str,
    from_amount: str,
    private_key: str,
    rpc_url: str,
    chain_id,
):
    try:
        allowance_amount = await get_allowance(web3, user, spender_address, from_token)
        nonce = await get_transaction_count(user, "pending", rpc_url, web3)
        data = await approve_transaction(
            session, str(chain_id), from_token, from_amount
        )

        if nonce is None:
            raise LookupError("Nonce not found")

        if int(allowance_amount) < int(from_amount):
            tx_object = {
                "nonce": nonce,
                "to": from_token,
                "gas": int(int(data["data"][0]["gasLimit"]) * 2),
                "gasPrice": int(int(data["data"][0]["gasPrice"]) * gas_ratio),
                "data": data["data"][0]["data"],
                "value": 0,
                "chainId": chain_id,
            }
            signed_tx = web3.eth.account.sign_transaction(tx_object, private_key)
            tx = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            try:
                await web3.eth.wait_for_transaction_receipt(tx, 60)
            except Exception:
                logging.exception("Error waiting for transaction receipt")
            return {"ok": True, "nonce": nonce}
        else:
            return {"ok": False, "nonce": nonce}
    except Exception:
        logging.exception("Error sending approve transaction")
        raise
