# -*- coding: utf-8 -*-
from typing import Dict
from typing import List

from moneybot.market import Order
from moneybot.market.state import MarketState
from moneybot.trade import AbstractTrade


def simulate_order(
    order: Order,
    balances: Dict[str, float],
) -> Dict[str, float]:
    """TODO: Docstring, state assumptions going into this simulation

    We can get fancier with this later, observe trends in actual trades we
    propose vs execute, and use that to make more realistic simulations!
    After all, our proposed price will not always be achievable.
    """
    if order.direction == Order.Direction.BUY:
        base_delta = -order.base_amount
        quote_delta = order.quote_amount
    else:
        base_delta = order.base_amount
        quote_delta = -order.quote_amount

    new = balances.copy()
    new[order.base_currency] = new.get(order.base_currency, 0) + base_delta
    new[order.quote_currency] = new.get(order.quote_currency, 0) + quote_delta
    return new


def simulate_trades(
    trades: List[AbstractTrade],
    market_state: MarketState,
) -> Dict[str, float]:
    """
    """
    new = market_state.balances.copy()

    for trade in trades:
        sell_amount = market_state.estimate_value(
            trade.reference_coin,
            trade.reference_value,
            trade.sell_coin,
        )
        new[trade.sell_coin] = new.get(trade.sell_coin, 0) - sell_amount

        buy_amount = market_state.estimate_value(
            trade.sell_coin,
            sell_amount,
            trade.buy_coin,
        )
        new[trade.buy_coin] = new.get(trade.buy_coin, 0) + buy_amount

    return new
