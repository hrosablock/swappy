from secrets import token_bytes
from sha3 import keccak_256

from coincurve import PublicKey
from cryptography.fernet import Fernet

from bot.env import FERNET_KEY

fernet = Fernet(FERNET_KEY)

def evm_generator():
    private_key = keccak_256(token_bytes(32)).digest()

    encrypted_key = fernet.encrypt(private_key)

    public_key = PublicKey.from_valid_secret(private_key).format(compressed=False)[1:]
    
    addr = keccak_256(public_key).digest()[-20:]
    return encrypted_key.decode(), f"0x{addr.hex()}"