import logging

import aiohttp
from pytoniq import Address

from bot.trading.TON.withdraw import send


async def get_address(collection, to_price):
    try:
        url = f"https://api.xrare.io/api/v1/collections/{collection}/nfts/filter"

        payload = {"toPrice": f"{to_price}", "sort": "price_low", "sale": "yes"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and data.get("ok") and data.get("nfts"):
                        nft = data.get("nfts")[0]
                        if (
                            nft.get("status") == "ok"
                            and nft.get("owner_type") == "sale"
                            and nft.get("currency") == "TON"
                            and float(nft.get("full_price")) <= float(to_price)
                            and nft.get("collection")
                            and Address(nft.get("collection").get("address")).to_str(
                                is_user_friendly=False
                            )
                            == Address(collection).to_str(is_user_friendly=False)
                            and nft.get("owner_address")
                            and await check(nft.get("owner_address"))
                        ):
                            return {
                                "ok": True,
                                "sale_address": nft.get("owner_address"),
                                "name": nft.get("name"),
                                "price": float(nft.get("full_price")),
                            }
                    return {"ok": False}

    except Exception as e:
        logging.exception(f"Failed to fetch TON nft for {collection} : {e}")
        return {"ok": False}


async def check(address):

    try:
        url = (
            f"https://tonapi.io/v2/blockchain/accounts/{address}/methods/get_sale_data"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data: dict = await response.json()
                if data and data.get("success") and not data.get("is_complete"):
                    return True
                else:
                    return False

    except Exception as e:
        logging.exception(f"{e} in check")
        return False


async def buy_nft(encrypted_mnemonic, collection: str, to_price: float):
    try:
        address = await get_address(collection, to_price)
        if address.get("ok"):
            destination = Address(address.get("sale_address")).to_str(
                is_user_friendly=False
            )
            amount = float(address.get("price")) + 0.6
            tx_hash = await send(encrypted_mnemonic, destination, amount)
            return tx_hash
        else:
            return None
    except Exception as e:
        logging.exception(f"Error in buy_nft: {e}")
        raise
