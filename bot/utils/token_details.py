import logging

from async_lru import alru_cache
from redis.asyncio import Redis
from web3 import AsyncWeb3

from bot.config import (
    chain_id_to_native_token_name,
    chain_id_to_rpc_url,
    evm_native_coin,
)
from bot.env import REDIS_URL

redis = Redis.from_url(REDIS_URL, decode_responses=True)


@alru_cache(maxsize=5000)
async def get_token_decimals(chain_id: int, token_address: str) -> int:
    try:
        if evm_native_coin.lower() == token_address.lower():
            return 18

        cache_key = f"decimals:{chain_id}:{token_address.lower()}"
        if (cached_decimals := await redis.get(cache_key)) is not None:
            return int(cached_decimals)

        web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(chain_id_to_rpc_url.get(chain_id)))
        if not await web3.is_connected():
            raise ConnectionError("Failed to connect to RPC")

        decimals_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            }
        ]
        token_contract = web3.eth.contract(
            address=web3.to_checksum_address(token_address), abi=decimals_abi
        )

        decimals = await token_contract.functions.decimals().call()
        await redis.set(cache_key, decimals, ex=864000)
        return decimals
    except Exception:
        logging.exception("Error getting token decimals")
        raise


@alru_cache(maxsize=5000)
async def get_token_name(chain_id: int, token_address: str) -> str:
    try:
        if evm_native_coin.lower() == token_address.lower():
            if chain_id_to_native_token_name.get(chain_id):
                return chain_id_to_native_token_name.get(chain_id)
            else:
                raise ValueError(f"Unsupported chain ID: {chain_id}")

        cache_key = f"name:{chain_id}:{token_address.lower()}"
        if (cached_name := await redis.get(cache_key)) is not None:
            return cached_name

        web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(chain_id_to_rpc_url.get(chain_id)))
        if not await web3.is_connected():
            raise ConnectionError("Failed to connect to RPC")

        name_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            }
        ]
        token_contract = web3.eth.contract(
            address=web3.to_checksum_address(token_address), abi=name_abi
        )

        token_name = await token_contract.functions.name().call()
        await redis.set(cache_key, token_name, ex=864000)
        return token_name
    except Exception:
        logging.exception("Error getting token name")
        raise
