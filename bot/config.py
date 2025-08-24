flood_delay = 0.5

bot_name = "swappy_web3_bot"

api_base_url = "https://web3.okx.com/api/v5/dex"


evm_native_coin = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

ton_native_coin = "TON"

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


gas_ratio = 2.5


chain_id_to_name = {
    1: "eth",
    10: "optimism",
    56: "bsc",
    137: "polygon",
    42161: "arbitrum",
    43114: "avalanche",
    8453: "base",
}

chain_id_to_native_token_name = {
    1: "ETH",
    10: "ETH",
    56: "BNB",
    137: "MATIC",
    42161: "ETH",
    43114: "AVAX",
    8453: "ETH",
}

chain_id_to_rpc_url = {
    1: "https://eth.drpc.org",
    10: "https://optimism.drpc.org",
    56: "https://bsc.drpc.org",
    137: "https://polygon.drpc.org",
    42161: "https://arbitrum.drpc.org",
    43114: "https://avalanche.drpc.org",
    8453: "https://base.drpc.org",
}

chain_id_to_tx_scan_url = {
    1: "https://etherscan.io/tx/",
    10: "https://optimistic.etherscan.io/tx/",
    56: "https://bscscan.com/tx/",
    137: "https://polygonscan.com/tx/",
    42161: "https://arbiscan.io/tx/",
    43114: "https://snowtrace.io/tx/",
    8453: "https://basescan.org/tx/",
}


approval_contract_addresses = {
    1: "0x40aA958dd87FC8305b97f2BA922CDdCa374bcD7f",
    10: "0x68D6B739D2020067D1e2F713b999dA97E4d54812",
    56: "0x2c34A2Fb1d0b4f55de51E1d0bDEfaDDce6b7cDD6",
    137: "0x3B86917369B83a6892f553609F3c2F439C184e31",
    42161: "0x70cBb871E8f30Fc8Ce23609E9E0Ea87B6b222F58",
    43114: "0x40aA958dd87FC8305b97f2BA922CDdCa374bcD7f",
    8453: "0x57df6092665eb6058DE53939612413ff4B09114E",
}

dex_router_addresses = {
    1: "0x7D0CcAa3Fac1e5A943c5168b6CEd828691b46B36",
    10: "0xf332761c673b59B21fF6dfa8adA44d78c12dEF09",
    56: "0x9333C74BDd1E118634fE5664ACA7a9710b108Bab",
    137: "0xA748D6573acA135aF68F2635BE60CB80278bd855",
    42161: "0xf332761c673b59B21fF6dfa8adA44d78c12dEF09",
    43114: "0x1daC23e41Fc8ce857E86fD8C1AE5b6121C67D96d",
    8453: "0x6b2C0c7be2048Daa9b5527982C29f48062B34D58",
}


limit_dex_router = {
    1: "0x2ae8947FB81f0AAd5955Baeff9Dcc7779A3e49F2",
    10: "0x2ae8947FB81f0AAd5955Baeff9Dcc7779A3e49F2",
    56: "0x2ae8947FB81f0AAd5955Baeff9Dcc7779A3e49F2",
    137: "0x2ae8947FB81f0AAd5955Baeff9Dcc7779A3e49F2",
    43114: "0x2ae8947FB81f0AAd5955Baeff9Dcc7779A3e49F2",
    42161: "0x2ae8947FB81f0AAd5955Baeff9Dcc7779A3e49F2",
}

limit_approval_contract = {
    1: "0x40aA958dd87FC8305b97f2BA922CDdCa374bcD7f",
    10: "0x68D6B739D2020067D1e2F713b999dA97E4d54812",
    56: "0x2c34A2Fb1d0b4f55de51E1d0bDEfaDDce6b7cDD6",
    137: "0x3B86917369B83a6892f553609F3c2F439C184e31",
    43114: "0x40aA958dd87FC8305b97f2BA922CDdCa374bcD7f",
    42161: "0x70cBb871E8f30Fc8Ce23609E9E0Ea87B6b222F58",
}


crosschain_dex_router = {
    1: "0x3b3ae790Df4F312e745D270119c6052904FB6790",
    10: "0xf332761c673b59B21fF6dfa8adA44d78c12dEF09",
    56: "0x9333C74BDd1E118634fE5664ACA7a9710b108Bab",
    137: "0xA748D6573acA135aF68F2635BE60CB80278bd855",
    43114: "0x1daC23e41Fc8ce857E86fD8C1AE5b6121C67D96d",
    42161: "0xf332761c673b59B21fF6dfa8adA44d78c12dEF09",
    8453: "0x6b2C0c7be2048Daa9b5527982C29f48062B34D58",
}

crosschain_approval_contract = {
    1: "0x40aA958dd87FC8305b97f2BA922CDdCa374bcD7f",
    10: "0x68D6B739D2020067D1e2F713b999dA97E4d54812",
    56: "0x2c34A2Fb1d0b4f55de51E1d0bDEfaDDce6b7cDD6",
    137: "0x3B86917369B83a6892f553609F3c2F439C184e31",
    43114: "0x40aA958dd87FC8305b97f2BA922CDdCa374bcD7f",
    42161: "0x70cBb871E8f30Fc8Ce23609E9E0Ea87B6b222F58",
    8453: "0x57df6092665eb6058DE53939612413ff4B09114E",
}

crosschain_xbridge_address = {
    1: "0xFc99f58A8974A4bc36e60E2d490Bb8D72899ee9f",
    56: "0xFc99f58A8974A4bc36e60E2d490Bb8D72899ee9f",
    137: "0x89f423567c2648BB828c3997f60c47b54f57Fa6e",
    43114: "0xf956D9FA19656D8e5219fd6fa8bA6cb198094138",
    42161: "0xFc99f58A8974A4bc36e60E2d490Bb8D72899ee9f",
    10: "0xf956D9FA19656D8e5219fd6fa8bA6cb198094138",
    8453: "0x5965851f21DAE82eA7C62f87fb7C57172E9F2adD",
}


limit_order_type = [
    {"name": "salt", "type": "uint256"},
    {"name": "makerToken", "type": "address"},
    {"name": "takerToken", "type": "address"},
    {"name": "maker", "type": "address"},
    {"name": "receiver", "type": "address"},
    {"name": "allowedSender", "type": "address"},
    {"name": "makingAmount", "type": "uint256"},
    {"name": "takingAmount", "type": "uint256"},
    {"name": "minReturn", "type": "uint256"},
    {"name": "deadLine", "type": "uint256"},
    {"name": "partiallyAble", "type": "bool"},
]


allowance_abi = [
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    }
]


cancel_limit_abi = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "salt", "type": "uint256"},
                    {
                        "internalType": "address",
                        "name": "makerToken",
                        "type": "address",
                    },
                    {
                        "internalType": "address",
                        "name": "takerToken",
                        "type": "address",
                    },
                    {"internalType": "address", "name": "maker", "type": "address"},
                    {"internalType": "address", "name": "receiver", "type": "address"},
                    {
                        "internalType": "address",
                        "name": "allowedSender",
                        "type": "address",
                    },
                    {
                        "internalType": "uint256",
                        "name": "makingAmount",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "takingAmount",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "minReturn", "type": "uint256"},
                    {"internalType": "uint256", "name": "deadLine", "type": "uint256"},
                    {"internalType": "bool", "name": "partiallyAble", "type": "bool"},
                ],
                "internalType": "struct OrderLibV2.Order",
                "name": "_order",
                "type": "tuple",
            }
        ],
        "name": "cancelOrder",
        "outputs": [
            {"internalType": "uint256", "name": "orderRemaining", "type": "uint256"},
            {"internalType": "bytes32", "name": "orderHash", "type": "bytes32"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]
