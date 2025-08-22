import itertools

from abc import ABC
from enum import Enum
from dataclasses import dataclass, field
from typing import NewType


MarketHashName = NewType("MarketHashName", str)


class OrderType(Enum):
    BUY = 'Buy'
    SELL = 'Sell'


class AgentType(Enum):
    NOVICE = 'Novice'
    TRADER = 'Trader'
    INVESTOR = 'Investor'
    FARMER = 'Farmer'


class ItemCategory(Enum):
    CONTAINER = 'Container'
    WEAPON_SKIN = 'WeaponSkin'
    STICKER = 'Sticker'
    MISC = 'Misc'


class ItemRarity(Enum):
    BASE_GRADE = 'BaseGrade'
    COMMON = 'Common'
    UNCOMMON = 'Uncommon'
    RARE = 'Rare'
    MYTHICAL = 'Mythical'
    LEGENDARY = 'Legendary'
    ANCIENT = 'Ancient'
    EXCEEDINGLY_RARE = 'ExceedinglyRare'


class WeaponExterior(Enum):
    FACTORY_NEW = 'Factory New'
    MINIMAL_WEAR = 'Minimal Wear'
    FIELD_TESTED = 'Field-Tested'
    WELL_WORN = 'Well-Worn'
    BATTLE_SCARRED = 'Battle-Scarred'


@dataclass(frozen=True, slots=True)
class MarketItem(ABC):
    """
    Base Item class, used as a `key` in dictionaries to group same `Items` but with different attributes together.

    Has general `Item` fields: name, rarity, category.
    """
    name: str
    rarity: ItemRarity
    category: ItemCategory
    market_hash_name: MarketHashName = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'market_hash_name', self.name)


@dataclass(frozen=True, slots=True)
class Container(MarketItem):
    """Container Instance. Describes it's content."""
    content: dict = None


@dataclass(frozen=True, slots=True)
class WeaponSkin(MarketItem):
    """Weapon Skin instance. Describes skin parameters: weapon exterior, float_value, pattern_index."""
    exterior: WeaponExterior
    float_value: float
    pattern_index: int
    
    def __post_init__(self):
        MarketItem.__post_init__(self)
        object.__setattr__(self, 'market_hash_name', f"{self.name} ({self.exterior.value})")


@dataclass(slots=True)
class InventoryItem:
    """Class for keeping `Item` information such as quantity and unlock_step only in Inventory."""
    item: MarketItem
    quantity: int
    unlock_step: int


_order_id = itertools.count()
_sale_id = itertools.count()


@dataclass(slots=True)
class Order:
    type: OrderType
    item: MarketItem
    price: int
    quantity: int
    agent_id: int
    step: int
    id: int = field(default_factory=lambda: next(_order_id))


@dataclass(frozen=True, slots=True)
class Sale:
    item: MarketItem
    price: int
    fee: int
    quantity: int
    buyer_id: int
    seller_id: int
    step: int
    id: int = field(default_factory=lambda: next(_sale_id))
