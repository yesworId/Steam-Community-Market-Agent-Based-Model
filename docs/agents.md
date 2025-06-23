# Agents

This section describes different types of representative agents used in simulation.
Each agent represents different types of behaviours observed on the `Steam Community Market`. 
Together they create dynamic and life, allowing simulation to closely model real-world digital trading environments.

### 🆕 Novice (Casual Player):
* Sells quickly to the highest `Buy Order`, sometimes even at a loss, to achieve immediate results;
* Actions are mostly illogical;
* Buys items to open or play with them.

Represents average `Market` participant, who does not care about profits, follows market trends, usually **impulsive**.
Such an agent adds noise and realism to the simulation, mimicking casual players' thoughtless actions, without economic reasoning.

### 📈 Trader (Flipper):
* Sees speculative value in items;
* Observes market patterns, actions are usually well-determined;
* Goal to maximize margins, make profit by reselling at higher prices.

Most of the time, sells his items higher than the bought price. 
Doesn't hurry and can wait for the right opportunity to sell. 
Buys multiple items at once before the start of a growth trend.

### 👨‍💼 Investor:
* Expects long-term profits, market speculator;
* Buys in big quantities, usually at lower prices and holds items for a long period;
* Selling after substantial growth in price.

Investors buy items, sometimes without worrying about getting the lowest price, seeking returns in the future.
They believe that the value of items will increase **significantly** over time and are willing to hold their items for years.
Sells items in batches, often looking for higher gains or in big chunks in case of investment failure.

### 💻 Farmer:
* High motivation to make a profit through system exploitation;
* Sells 'farmed' items in range of median price, in addition, does not buy items from `Market`;
* They aim to recoup the money spent on the entire infrastructure and get passive income.

Farmers load larger quantities of items on the `Market` compared to casual users.
Nevertheless, they are trying to sell items in **batches**, to not dump prices short term.
In case of a potential account ban, they may decide to sell in **bulk**. 
Farmers are primarily concerned with maximizing their final profit.

In this context "**farming**" means launching as many accounts simultaneously as your machine can handle to then receive in-game rewards or items by performing certain actions, often using tools and scripts.

## Summary
Agents are autonomous entities, which imitate real-life users, each with their own motivations, strategies, and goals.
Simulation is based on a heterogeneous agent model, where different agent types interact with the `Market` environment and each other. 
A more in depth look on how agents behave can be found in the `agents.py` module, specifically in agent class and methods` docstrings.
