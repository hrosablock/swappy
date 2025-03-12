import logging
import sys

from tonutils.client import ToncenterClient
from tonutils.wallet import WalletV4R2

from bot.env import TONCENTER_API_KEY
from bot.utils.dex import decrypt_mnemonic

async def send(encrypted_mnemonic:str, destination:str, amount:float):
    try:
        mnemonic = decrypt_mnemonic(encrypted_mnemonic).split()
        client = ToncenterClient(api_key=TONCENTER_API_KEY, is_testnet=False)
        wallet = WalletV4R2.from_mnemonic(client, mnemonic)[0]

        return await wallet.transfer(destination=destination, amount=amount)

    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
        raise


async def send_jetton(encrypted_mnemonic:str, destination:str, jetton_amount:float, jetton_master_address:str, jetton_decimals:int, ):
    try:
        mnemonic = decrypt_mnemonic(encrypted_mnemonic).split()
        client = ToncenterClient(api_key=TONCENTER_API_KEY, is_testnet=False)
        wallet = WalletV4R2.from_mnemonic(client, mnemonic)[0]

        return await wallet.transfer_jetton(destination=destination, jetton_amount=jetton_amount, jetton_master_address=jetton_master_address, jetton_decimals=jetton_decimals)

    except Exception as e:
        logging.exception(f"Error in {sys._getframe().f_code.co_name}: {e}")
        raise