from secrets import token_bytes
import logging

from pytoniq import WalletV4R2, LiteClient

from coincurve import PublicKey
from cryptography.fernet import Fernet
from sha3 import keccak_256

from bot.env import FERNET_KEY

fernet = Fernet(FERNET_KEY)


def evm_generator():
    private_key = keccak_256(token_bytes(32)).digest()

    encrypted_key = fernet.encrypt(private_key)

    public_key = PublicKey.from_valid_secret(private_key).format(compressed=False)[1:]

    addr = keccak_256(public_key).digest()[-20:]
    return encrypted_key.decode(), f"0x{addr.hex()}"


async def ton_generator():
    client = LiteClient.from_mainnet_config(ls_i=2, trust_level=2, timeout=15)
    await client.connect()
    wallet = await WalletV4R2.create(provider=client, wc=0)
    
    mnemonic = " ".join(wallet[0])
    encrypted_mnemonic = fernet.encrypt(mnemonic.encode()).decode()
    
    await client.close()
    return encrypted_mnemonic, wallet[1].address.to_str(is_user_friendly=True, is_bounceable=False)
