import gc
import random

import numpy as np
import pandas as pd

from statistics import mean, stdev
from multiprocessing import Pool

from abm import Market, DropGenerator, AgentType, NoviceAgent, TraderAgent, InvestorAgent, FarmerAgent
from abm.metrics import calculate_weighted_mean_price, get_all_sales, calculate_total_fee


MARKET_FEES = [0.10, 0.20, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
NUMBER_OF_AGENTS = 1000
NUMBER_OF_STEPS = 75_000
NUMBER_OF_SIMULATIONS = 100

MIN_BALANCE = 0
MAX_BALANCE = 2000
MEAN_BALANCE = 650
STD_DEV_BALANCE = 300

MIN_NUMBER_OF_ACCOUNTS = 1
MAX_NUMBER_OF_ACCOUNTS = 1000
MEAN_NUMBER_OF_ACCOUNTS = 100
STD_DEV_ACCOUNT_NUMBERS = 50

BASE_DROP_CHANCE = 0.6
STEPS_PER_DAY = 1000
MAX_DROPS_PER_WEEK = 1

AGENT_WEIGHTS = {
    AgentType.NOVICE: 0.4,
    AgentType.TRADER: 0.2,
    AgentType.INVESTOR: 0.3,
    AgentType.FARMER: 0.1,
}

ITEMS_DICT = {
    'Item A': 1.0
}


def generate_agents(market, rng, np_rng, num_agents=1000, weights=None):
    if weights is None:
        weights = {
            AgentType.NOVICE: 0.25,
            AgentType.TRADER: 0.25,
            AgentType.INVESTOR: 0.25,
            AgentType.FARMER: 0.25,
        }
    types, probs = zip(*weights.items())

    balances = np_rng.normal(MEAN_BALANCE, STD_DEV_BALANCE, num_agents)
    balances = np.clip(balances, MIN_BALANCE, MAX_BALANCE)

    farm_sizes = np_rng.normal(MEAN_NUMBER_OF_ACCOUNTS, STD_DEV_ACCOUNT_NUMBERS, num_agents)
    farm_sizes = np.clip(
        np.round(farm_sizes), MIN_NUMBER_OF_ACCOUNTS, MAX_NUMBER_OF_ACCOUNTS
    ).astype(int)

    agents = []
    for i in range(num_agents):
        agent_type = rng.choices(types, weights=probs, k=1)[0]
        balance = int(balances[i] * 100)
        impulsivity = rng.random()

        if agent_type == AgentType.NOVICE:
            agent = NoviceAgent(i, market, agent_type, balance, impulsivity)
        elif agent_type == AgentType.TRADER:
            risk_tolerance = rng.random()
            agent = TraderAgent(i, market, agent_type, balance, impulsivity, risk_tolerance)
        elif agent_type == AgentType.INVESTOR:
            risk_tolerance = rng.random()
            agent = InvestorAgent(i, market, agent_type, balance, impulsivity, risk_tolerance)
        else:
            number_of_accounts = int(farm_sizes[i])
            agent = FarmerAgent(i, market, agent_type, balance, impulsivity, number_of_accounts)

        agents.append(agent)
    return agents


def run_single_simulation(market_fee: float, steps: int = 100_000, seed=None):
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    market = Market(market_fee=market_fee, steps_per_day=STEPS_PER_DAY)
    agents = generate_agents(market, rng, np_rng, num_agents=NUMBER_OF_AGENTS, weights=AGENT_WEIGHTS)
    market.add_agents(agents)

    drop_generator = DropGenerator(
        agents=agents,
        market=market,
        items_drop_pool=ITEMS_DICT,
        base_drop_chance=BASE_DROP_CHANCE,
        max_drops_per_week=MAX_DROPS_PER_WEEK
    )

    for step in range(steps):
        market.current_step = step
        drop_generator.tick(step)

        agent = rng.choice(agents)
        agent.act()

    total_sales = len(get_all_sales(market.sales_history))
    avg_price = calculate_weighted_mean_price(market.sales_history, 'Item A', number_of_sales=total_sales)
    print("SIMULATION FINISHED!")
    result = {
        'fee': market_fee,
        'total_sales': total_sales,
        'avg_price': avg_price,
        'total_fee': calculate_total_fee(market.sales_history)
    }

    try:
        del market, agents, drop_generator
        gc.collect()
    except Exception as ex:
        print(f"COULDN'T DELETE DATA: {ex}")
        pass

    return result


def worker(args):
    fee, seed = args
    return run_single_simulation(fee, NUMBER_OF_STEPS, seed=seed)


def main():
    tasks = [(fee, int(fee*100)+i) for fee in MARKET_FEES for i in range(NUMBER_OF_SIMULATIONS)]
    with Pool() as pool:
        results = pool.map(worker, tasks)

    results_by_fee = {}
    for (fee, _), res in zip(tasks, results):
        results_by_fee.setdefault(fee, []).append(res)
    summary = []
    for fee in MARKET_FEES:
        batch = results_by_fee.get(fee, [])
        avg_sales = mean(r['total_sales'] for r in batch) if batch else 0.0
        std_sales = stdev(r['total_sales'] for r in batch) if len(batch) > 1 else 0.0
        avg_price = mean(r['avg_price'] for r in batch) if batch else 0.0
        std_price = stdev(r['avg_price'] for r in batch) if len(batch) > 1 else 0.0
        avg_total_fee = mean(r['total_fee'] for r in batch) if batch else 0.0
        std_total_fee = stdev(r['total_fee'] for r in batch) if len(batch) > 1 else 0.0
        summary.append({
            'fee': fee,
            'avg_sales': avg_sales,
            'std_sales': std_sales,
            'avg_price': avg_price,
            'std_price': std_price,
            'avg_total_fee': avg_total_fee,
            'std_total_fee': std_total_fee,
        })
    df = pd.DataFrame(summary)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    df.to_csv("results.csv", index=False)
    print(df)


if __name__ == "__main__":
    main()
