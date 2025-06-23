import math


def round_to_cents(price: float) -> float:
    return math.floor(price * 100) / 100.0


def refresh_entry_prices_from_history(self):
    # TODO: REFACTOR
    # Possible unnatural logic is when agent sold his weekly drop and it still calculated in the new entry_prices
    # although he got it for free
    purchases = self.market.get_agent_purchases(self.id)
    if not purchases:
        return {}

    sales = self.market.get_agent_sales(self.id)

    by_item = {}
    for p in purchases:
        info = by_item.setdefault(p.item_name, {'bought_qty': 0, 'bought_cost': 0.0, 'sold_qty': 0})
        info['bought_qty'] += p.quantity
        info['bought_cost'] += p.quantity * p.price
    for s in sales:
        info = by_item.setdefault(s.item_name, {'bought_qty': 0, 'bought_cost': 0.0, 'sold_qty': 0})
        info['sold_qty'] += s.quantity

    new_entry = {}
    for item, info in by_item.items():
        bq = info['bought_qty']
        if bq == 0:
            continue
        sq = info['sold_qty']
        net_qty = bq - sq
        if net_qty <= 0:
            continue

        total_cost = info['bought_cost']
        if sq > 0:
            avg_buy = info['bought_cost'] / bq
            total_cost -= avg_buy * sq

        new_entry[item] = {
            'qty': net_qty,
            'avg_price': round(total_cost / net_qty, 2)
        }

    return new_entry
