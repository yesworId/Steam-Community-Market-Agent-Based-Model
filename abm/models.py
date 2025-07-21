import itertools
from enum import Enum
from dataclasses import dataclass, field


class OrderType(Enum):
    BUY = 'buy'
    SELL = 'sell'


class AgentType(Enum):
    NOVICE = 'novice'
    TRADER = 'trader'
    INVESTOR = 'investor'
    FARMER = 'farmer'


_order_id = itertools.count()
_sale_id = itertools.count()


@dataclass
class Order:
    type: OrderType
    item_name: str
    price: int
    quantity: int
    agent_id: int
    step: int
    id: int = field(default_factory=lambda: next(_order_id))


@dataclass
class Sale:
    item_name: str
    price: int
    fee: int
    quantity: int
    buyer_id: int
    seller_id: int
    step: int
    id: int = field(default_factory=lambda: next(_sale_id))
