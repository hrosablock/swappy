from enum import Enum


class StatusEnum(str, Enum):
    active = "active"
    completed = "completed"
    canceled = "canceled"

class ChainType(str, Enum):
    EVM = "EVM"
    SOL = "SOL"
    TON = "TON"

class ChainID(int, Enum):
    ETHEREUM = 1
    OP = 10
    BSC = 56
    POLYGON = 137
    ARBITRUM = 42161
    AVALANCHE = 43114
    BASE = 8453

class OrderType(str, Enum):
    LIMIT = "limit"
    TP_SL = "tp/sl"

class Direction(str, Enum):
    ABOVE = "above"
    BELOW = "below"