import logging

import aiohttp
from aiogram import html
from async_lru import alru_cache
from eth_utils import to_checksum_address
from redis.asyncio import Redis
from web3 import AsyncWeb3

from bot.config import chain_id_to_name, chain_id_to_rpc_url, evm_native_coin
from bot.env import MORALIS_API_KEY, REDIS_URL

redis = Redis.from_url(REDIS_URL, decode_responses=True)


@alru_cache(maxsize=5000, ttl=10)
async def get_balance(chain_id: int, wallet_address: str, token_address: str) -> int:
    try:
        cache_key = f"balance:{chain_id}:{wallet_address.lower()}:{token_address.lower()}"
        if (cached_balance := await redis.get(cache_key)) is not None:
            return int(cached_balance)

        web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(chain_id_to_rpc_url.get(chain_id)))
        if not await web3.is_connected():
            raise ConnectionError("Failed to connect to RPC")

        if evm_native_coin.lower() == token_address.lower():
            balance = int(await web3.eth.get_balance(web3.to_checksum_address(wallet_address)))
        else:
            balance_abi = [{"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"}]
            token_contract = web3.eth.contract(address=web3.to_checksum_address(token_address), abi=balance_abi)
            balance = int(await token_contract.functions.balanceOf(web3.to_checksum_address(wallet_address)).call())

        await redis.set(cache_key, str(balance), ex=10)
        return balance
    except Exception:
        logging.exception(f"Error getting balance for {wallet_address} on chain {chain_id} for token {token_address}")
        raise


@alru_cache(maxsize=5000, ttl=30)
async def fetch_erc20_balances(address:str, chain_id:int) -> list:
    try:
        network = chain_id_to_name.get(chain_id)
        if not network:
            raise ValueError(f"Unsupported chain ID: {chain_id}")
        URL = f"https://deep-index.moralis.io/api/v2.2/{to_checksum_address(address)}/erc20?chain={network}&exclude_spam=true"
        headers = {
            "accept": "application/json",
            "X-API-Key": MORALIS_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(URL, headers=headers) as response:
                tokens = await response.json()

                result = []
                formatted_result = ""
                if not tokens:
                    return result, formatted_result
                
                for token in tokens:
                    name = token.get("name", "")
                    symbol = token.get("symbol", "")
                    if not name and not symbol:
                        continue
                    
                    token_address = token.get("token_address", "")
                    balance = token.get("balance", "")
                    decimals = token.get("decimals")
                    
                    if (not token_address or not balance or decimals is None or
                        not isinstance(balance, str) or not balance.isdigit() or int(balance) <= 0 or
                        not isinstance(decimals, int) or decimals < 0):
                        continue
                    
                    balance = int(balance)
                    blnce = round(balance / (10 ** decimals), decimals)
                    formatted_balance = f"{blnce:.{decimals}f}"
                    
                    display_name = f"{name}({symbol})" if name and symbol else name or symbol

                    result.append({"name": display_name, "token_address":token_address, "balance":balance, "decimals":decimals})
                    formatted_result += f"\n\n{display_name}: {formatted_balance}   \n{html.code(token_address)}"
                
                return result, formatted_result
    except Exception:
        logging.exception(f"Failed to fetch ERC20 balances for {address} on chain id {chain_id})")
        return [], ""