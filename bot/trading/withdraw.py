import logging

from eth_utils import to_checksum_address
from web3 import AsyncWeb3

from bot.config import chain_id_to_rpc_url, evm_native_coin
from bot.utils.dex import decrypt_key

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


async def send(encrypted_key: str, chain_id: int, amount: int, token_address: str, to_wallet: str):
    try:
        token_address = to_checksum_address(token_address) if token_address else None
        to_wallet = to_checksum_address(to_wallet)

        private_key = decrypt_key(encrypted_key)
        rpc_url = chain_id_to_rpc_url.get(chain_id)
        if not rpc_url:
            raise ValueError(f"Unsupported chain ID: {chain_id}")

        web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        if not await web3.is_connected():
            raise ConnectionError("Failed to connect to RPC")

        account = web3.eth.account.from_key(private_key)
        nonce = await web3.eth.get_transaction_count(account.address)
        gas_price = await web3.eth.gas_price

        if not token_address or token_address.lower() == evm_native_coin.lower():
            gas_limit = await web3.eth.estimate_gas({
                "from": account.address,
                "to": to_wallet,
                "value": amount
            })
            txn = {
                "to": to_wallet,
                "value": amount,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": chain_id
            }
        else:
            contract = web3.eth.contract(address=token_address, abi=[
                {"constant": False, "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}], "name": "transfer", 
                    "outputs": [{"name": "", "type": "bool"}], "type": "function"}
            ])
            txn = await contract.functions.transfer(to_wallet, amount).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "gasPrice": gas_price,
                "chainId": chain_id
            })
            txn["gas"] = await web3.eth.estimate_gas(txn)

        signed_txn = account.sign_transaction(txn)
        tx_hash = await web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return tx_hash.hex()
    except Exception:
        logging.exception("Error sending transaction")
        raise
