import random
import numpy as np

from abm import Market, DropGenerator, AgentType, NoviceAgent, TraderAgent, InvestorAgent, FarmerAgent
from abm.metrics import get_all_sales, calculate_total_fee
from abm.models import Container, ItemCategory, ItemRarity
from visualization import plots

MARKET_FEE = 0.15
STEPS_PER_DAY = 1000
TRADE_LOCK_PERIOD = 7

NUMBER_OF_AGENTS = 1000
NUMBER_OF_STEPS = 75_000

MIN_BALANCE = 0
MAX_BALANCE = 2000
MEAN_BALANCE = 650
STD_DEV_BALANCE = 300

MIN_NUMBER_OF_ACCOUNTS = 1
MAX_NUMBER_OF_ACCOUNTS = 1000
MEAN_NUMBER_OF_ACCOUNTS = 100
STD_DEV_ACCOUNT_NUMBERS = 50

BASE_DROP_CHANCE = 0.6
MAX_DROPS_PER_WEEK = 1
TRADE_LOCK_ON = True

AGENT_WEIGHTS = {
    AgentType.NOVICE: 0.4,
    AgentType.TRADER: 0.2,
    AgentType.INVESTOR: 0.3,
    AgentType.FARMER: 0.1,
}

ITEMS_DICT = {
    Container('Case A', ItemRarity.BASE_GRADE, ItemCategory.CONTAINER): 1.0
}


def generate_agents(num_agents: int = 1000, weights: dict = None):
    if weights is None:
        weights = {
            AgentType.NOVICE: 0.25,
            AgentType.TRADER: 0.25,
            AgentType.INVESTOR: 0.25,
            AgentType.FARMER: 0.25,
        }
    types, probs = zip(*weights.items())

    balances = np.random.normal(MEAN_BALANCE, STD_DEV_BALANCE, num_agents)
    balances = np.clip(balances, MIN_BALANCE, MAX_BALANCE)

    farm_sizes = np.random.normal(MEAN_NUMBER_OF_ACCOUNTS, STD_DEV_ACCOUNT_NUMBERS, num_agents)
    farm_sizes = np.clip(
        np.round(farm_sizes), MIN_NUMBER_OF_ACCOUNTS, MAX_NUMBER_OF_ACCOUNTS
    ).astype(int)

    agents = []
    for i in range(num_agents):
        agent_type = random.choices(types, weights=probs, k=1)[0]
        balance = int(balances[i] * 100)
        impulsivity = random.random()

        if agent_type == AgentType.NOVICE:
            agent = NoviceAgent(i, None, agent_type, balance, impulsivity)
        elif agent_type == AgentType.TRADER:
            risk_tolerance = random.random()
            agent = TraderAgent(i, None, agent_type, balance, impulsivity, risk_tolerance)
        elif agent_type == AgentType.INVESTOR:
            risk_tolerance = random.random()
            agent = InvestorAgent(i, None, agent_type, balance, impulsivity, risk_tolerance)
        else:
            number_of_accounts = int(farm_sizes[i])
            agent = FarmerAgent(i, None, agent_type, balance, impulsivity, number_of_accounts)

        agents.append(agent)
    return agents


def run_simulation():
    market = Market(
        market_fee=MARKET_FEE,
        steps_per_day=STEPS_PER_DAY,
        trade_lock_period=TRADE_LOCK_PERIOD
    )
    agents = generate_agents(NUMBER_OF_AGENTS, AGENT_WEIGHTS)
    market.add_agents(agents)

    drop_generator = DropGenerator(
        agents=agents,
        market=market,
        items_drop_pool=ITEMS_DICT,
        base_drop_chance=BASE_DROP_CHANCE,
        max_drops_per_week=MAX_DROPS_PER_WEEK,
        trade_lock_on=TRADE_LOCK_ON
    )

    # plots.agent_balance_histogram(agents)

    for step in range(NUMBER_OF_STEPS):
        market.current_step = step
        print(f"STEP: {step}")
        drop_generator.tick(step)

        agent = random.choice(agents)
        agent.act()

    for item in ITEMS_DICT.keys():
        plots.plot_sales_history(market.sales_history, item.market_hash_name)
        # plots.plot_sales_history(market.sales_history, item.market_hash_name, STEPS_PER_DAY, show_volume=True)
        plots.plot_order_book(market, item.market_hash_name)

    print("Number of Sales:", len(get_all_sales(market.sales_history)))
    print("Total Fee:", calculate_total_fee(market.sales_history))


if __name__ == "__main__":
    run_simulation()
