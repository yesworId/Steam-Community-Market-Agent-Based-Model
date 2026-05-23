import random
import itertools

from abc import ABC
from enum import Enum, StrEnum
from dataclasses import dataclass, field
from typing import NewType, TypeAlias, DefaultDict


OrderID = NewType("OrderID", int)
AgentID = NewType("AgentID", int)
MarketHashName = NewType("MarketHashName", str)


class OrderType(Enum):
    BUY = 'Buy'
    SELL = 'Sell'


class AgentType(StrEnum):
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
    """
    Represents CS2 internal item rarity names.
    """

    BASE_GRADE = 'BaseGrade'
    """Base Grade (Stock), usually containers"""

    COMMON = 'Common'
    """Consumer Grade (White)"""

    UNCOMMON = 'Uncommon'
    """Industrial Grade (Light blue)"""
    
    RARE = 'Rare'
    """Mil-Spec Grade (Blue)"""
    
    MYTHICAL = 'Mythical'
    """Restricted (Purple)"""
    
    LEGENDARY = 'Legendary'
    """Classified (Pink)"""
    
    ANCIENT = 'Ancient'
    """Covert (Red)"""

    IMMORTAL = 'Immortal'
    """Contraband (Orange)"""
    
    EXCEEDINGLY_RARE = 'ExceedinglyRare'
    """Exceedingly Rare (Gold - Knives/Gloves)"""


class WeaponExterior(Enum):
    FACTORY_NEW = 'Factory New'
    MINIMAL_WEAR = 'Minimal Wear'
    FIELD_TESTED = 'Field-Tested'
    WELL_WORN = 'Well-Worn'
    BATTLE_SCARRED = 'Battle-Scarred'


@dataclass(frozen=True, slots=True)
class MarketItem(ABC):
    """
    Base abstract class for all tradeable items in the simulation.

    Provides general attributes shared by every item type. 
    `market_hash_name` is a canonical string identifier that matches 
    Steam's internal naming scheme (used as a key in dictionaries).
    """
    name: str
    rarity: ItemRarity
    category: ItemCategory
    market_hash_name: MarketHashName = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'market_hash_name', self.name)


@dataclass(frozen=True, slots=True)
class ContainerTier:
    """
    Represents a single rarity tier in Container's drop pool.
 
    Attributes:
        rarity: Rarity of items in this tier.
        items: List of items in this tier.
        seed_price_cents: Reference price registered before 
            any real sale exist.
    """
    rarity:           ItemRarity
    items:            tuple[MarketItem, ...]
    seed_price_cents: int


DEFAULT_DROP_PROBABILITIES: dict[ItemRarity, float] = {
    ItemRarity.RARE:                0.7992,   # Mil-Spec
    ItemRarity.MYTHICAL:            0.1598,   # Restricted  
    ItemRarity.LEGENDARY:           0.0320,   # Classified
    ItemRarity.ANCIENT:             0.0064,   # Covert
    ItemRarity.EXCEEDINGLY_RARE:    0.0026,   # Knife / Gloves
}

# Pre-computed defaults
_DEFAULT_RARITIES: list[ItemRarity] = list(DEFAULT_DROP_PROBABILITIES.keys())
_DEFAULT_WEIGHTS:  list[float] = list(DEFAULT_DROP_PROBABILITIES.values())

# Cache for custom probability lists — keyed by the container's drop_probabilities tuple
_DROP_LISTS_CACHE: dict[
    tuple[tuple[ItemRarity, float], ...],
    tuple[list[ItemRarity], list[float]]
] = {}

def _get_drop_lists(
    drop_probabilities: tuple[tuple[ItemRarity, float], ...] | None
) -> tuple[list[ItemRarity], list[float]]:
    """
    Returns (rarities, weights) pre-computed for random.choices.

    - If drop_probabilities is None, returns module-level defaults.
    """
    if drop_probabilities is None:
        return _DEFAULT_RARITIES, _DEFAULT_WEIGHTS

    if drop_probabilities not in _DROP_LISTS_CACHE:
        rarities, weights = zip(*drop_probabilities)
        _DROP_LISTS_CACHE[drop_probabilities] = (list(rarities), list(weights))

    return _DROP_LISTS_CACHE[drop_probabilities]


@dataclass(frozen=True, slots=True)
class Container(MarketItem):
    """
    In-game container (case, capsule, package) that can be opened for loot inside.

    Attributes:
        tiers: Available loot rarity tiers.
        drop_probabilities: Probabilities grouped by rarities.
    """
    tiers:              tuple[ContainerTier, ...] | None = None
    drop_probabilities: tuple[tuple[ItemRarity, float], ...] | None = None
 
    def roll_drops(self, quantity: int = 1) -> list[MarketItem]:
        """
        Rolls picked number of container openings.
 
        Uses a single random.choices call for bulk efficiency.
 
        Returns:
            List of dropped MarketItems (may be shorter than quantity
            if some rolls hit none present rarities in tiers).
        """
        if not self.tiers:
            return []
 
        rarities, weights = _get_drop_lists(self.drop_probabilities)
        tier_map: dict[ItemRarity, ContainerTier] = {t.rarity: t for t in self.tiers}
        rolled_rarities = random.choices(rarities, weights=weights, k=quantity)
 
        results: list[MarketItem] = []
        for rarity in rolled_rarities:
            tier = tier_map.get(rarity)
            if tier:
                results.append(random.choice(tier.items))
 
        return results
 
    def get_seed_prices(self) -> dict[MarketHashName, int]:
        """
        Returns {market_hash_name: seed_price_cents} for all items in all tiers.
        Used to pre-register prices in Market before any sales occur.
        """
        if not self.tiers:
            return {}
        prices: dict[MarketHashName, int] = {}
        for tier in self.tiers:
            for item in tier.items:
                prices.setdefault(item.market_hash_name, tier.seed_price_cents)
        return prices


@dataclass(frozen=True, slots=True)
class WeaponSkin(MarketItem):
    """
    Describes skin parameters: weapon exterior, float_value, pattern_index.
    Overrides `market_hash_name` with its exterior.
    """
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
    agent_id: AgentID
    step: int
    id: OrderID = field(default_factory=lambda: OrderID(next(_order_id)))


@dataclass(frozen=True, slots=True)
class Sale:
    item: MarketItem
    price: int
    total_fee: int
    quantity: int
    buyer_id: AgentID
    seller_id: AgentID
    step: int
    id: int = field(default_factory=lambda: next(_sale_id))


SalesHistory: TypeAlias = DefaultDict[MarketHashName, list[Sale]]
AgentMarketHistory: TypeAlias = DefaultDict[AgentID, list[Sale]]
AgentBuyOrderIndex: TypeAlias = dict[AgentID, dict[MarketHashName, OrderID]]

@dataclass(slots=True)
class EntryPrice:
    avg_price: int
    quantity: int

@dataclass(slots=True, frozen=True)
class ActiveAgentsResult:
    count: int
    fraction: float
    by_type: dict[AgentType, int]

@dataclass(slots=True, frozen=True)
class AgentPnL:
    revenue: float
    spending: float
    pnl: float
    roi_pct: float
    unbox_rewards_value: float
    num_sales: int
    num_purchases: int