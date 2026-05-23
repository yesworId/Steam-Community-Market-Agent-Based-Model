# Market

`Market` class simulates real-life trading environment - [Steam Community Market](https://steamcommunity.com/market/). 
It serves as a central trading system, where `Agents` interact with each other. 
This class completely simulates real mechanisms and business logic on Steam Community Market: 

* sorts `Orders` in correct order.
* returns list of `Orders` of given type or list of recent `Sales` for specific item.
* matches `Orders` based on price and "*first come, first served*" principle.
* validates purchase, does all monetary calculations, balance updates and item transfer.
* records history of every `Sale`.

## Parameters:
- `market_fee`: Percentage, which `Market` charges on every Sale.
- `steps_per_day`: Number of simulation steps per simulated day.
- `trade_lock_period`: Trade hold duration (in simulation days).
- `lock_on_purchase`: If True, applies trade lock to items purchased from the market.
- `max_balance`: The maximum balance capacity allowed for any Agent.
- `current_step`: Counter of simulation steps.

Buy and Sell `Orders` are stored in `SortedList` data structure. 
It automatically sorts them in corresponding order and allows quickly filter or access them.
Each completed market transaction is recorded in `sales_history` dictionary with list of sales for each Item.

**NOTE:** 
User is responsible for adding generated agents after initializing Market instance!