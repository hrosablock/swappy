import logging
import sys

import aiohttp
from pytoniq_core import Address
from tonutils.client import TonapiClient
from tonutils.jetton.dex.stonfi import StonfiRouterV2
from tonutils.jetton.dex.stonfi.v2.pton.constants import PTONAddresses
from tonutils.utils import to_amount
from tonutils.wallet import WalletV4R2

from bot.env import TONAPI_API_KEY
from bot.utils.dex import decrypt_mnemonic


async def get_router_address(from_token: str, to_token: str, amount: int) -> str:
    url = "https://api.ston.fi/v1/swap/simulate"
    headers = {"Accept": "application/json"}
    params = {
        "offer_address": from_token,
        "ask_address": to_token,
        "units": amount,
        "slippage_tolerance": 0.2,
        "dex_v2": "true",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, headers=headers) as response:
            if response.status == 200:
                content = await response.json()
                return content.get("router_address")
            else:
                error_text = await response.text()
                raise Exception(
                    f"Failed to get router address: {response.status}: {error_text}"
                )


async def ton_to_jetton(encrypted_mnemonic: str, token: str, amount: int):
    try:
        mnemonic = decrypt_mnemonic(encrypted_mnemonic).split()
        client = TonapiClient(api_key=TONAPI_API_KEY, is_testnet=False)
        wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic)

        router_address = await get_router_address(PTONAddresses.MAINNET, token, amount)
        stonfi_router = StonfiRouterV2(client, router_address=router_address)

        to, value, body = await stonfi_router.get_swap_ton_to_jetton_tx_params(
            user_wallet_address=wallet.address.to_str(is_bounceable=True),
            receiver_address=wallet.address,
            refund_address=wallet.address,
            excesses_address=wallet.address,
            offer_jetton_address=Address(token),
            offer_amount=amount,
            min_ask_amount=int(amount * 0.9),
        )

        tx_hash = await wallet.transfer(
            destination=to, amount=to_amount(value), body=body
        )
        return tx_hash

    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
        raise


async def jetton_to_ton(encrypted_mnemonic: str, token: str, amount: int):
    try:
        mnemonic = decrypt_mnemonic(encrypted_mnemonic).split()
        client = TonapiClient(api_key=TONAPI_API_KEY, is_testnet=False)
        wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic)

        router_address = await get_router_address(token, PTONAddresses.MAINNET, amount)
        stonfi_router = StonfiRouterV2(client, router_address=router_address)

        to, value, body = await stonfi_router.get_swap_jetton_to_ton_tx_params(
            offer_jetton_address=Address(token),
            receiver_address=wallet.address,
            user_wallet_address=wallet.address,
            offer_amount=amount,
            refund_address=wallet.address,
            excesses_address=wallet.address,
            min_ask_amount=int(amount * 0.9),
        )

        tx_hash = await wallet.transfer(
            destination=to, amount=to_amount(value), body=body
        )

        return tx_hash

    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
        raise


async def jetton_to_jetton(
    encrypted_mnemonic: str, from_token: str, to_token: str, amount: int
):
    try:
        mnemonic = decrypt_mnemonic(encrypted_mnemonic).split()
        client = TonapiClient(api_key=TONAPI_API_KEY, is_testnet=False)
        wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic)

        router_address = await get_router_address(from_token, to_token, amount)
        stonfi_router = StonfiRouterV2(client, router_address=router_address)

        to, value, body = await stonfi_router.get_swap_jetton_to_jetton_tx_params(
            user_wallet_address=wallet.address,
            receiver_address=wallet.address,
            refund_address=wallet.address,
            excesses_address=wallet.address,
            offer_jetton_address=Address(from_token),
            ask_jetton_address=Address(to_token),
            offer_amount=amount,
            min_ask_amount=int(amount * 0.9),
        )

        tx_hash = await wallet.transfer(
            destination=to, amount=to_amount(value), body=body
        )

        return tx_hash

    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
        raise
