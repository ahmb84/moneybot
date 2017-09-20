# -*- coding: utf-8 -*-
from datetime import datetime

from pyloniex.constants import OrderType

from moneybot.market import Order
from moneybot.market.state import MarketState
from moneybot.trade import AbstractTrade
from moneybot.utils import simulate_order
from moneybot.utils import simulate_trades


def test_simulate_buy_order():
    # Buy 2 ETH at 0.07423378 BTC/ETH
    buy = Order(
        'BTC_ETH',
        0.07423378,
        2,
        Order.Direction.BUY,
        OrderType.fill_or_kill,
    )
    balances = {'BTC': 1.0}
    result = simulate_order(buy, balances)
    assert result == {
        'BTC': 0.85153244,
        'ETH': 2,
    }


def test_simulate_sell_order():
    # Sell 1.5 ETH at 0.07414017 BTC/ETH
    sell = Order(
        'BTC_ETH',
        0.07414017,
        1.5,
        Order.Direction.SELL,
        OrderType.fill_or_kill,
    )
    balances = {'BTC': 1.0, 'ETH': 5}
    result = simulate_order(sell, balances)
    assert result == {
        'BTC': 1.11121025500000001,
        'ETH': 3.5,
    }


def test_simulate_trades():
    trades = [
        # Sell 0.5 BTC worth of BTC to buy ETH
        # -0.5 BTC, +6.737858883631113 ETH
        AbstractTrade('BTC', 'ETH', 'BTC', 0.5),
        # Sell 5 BCH worth of BTC to buy ETH
        # -0.60083005 BTC, +8.096616179890052 ETH
        AbstractTrade('BTC', 'ETH', 'BCH', 5),
        # Sell 1 ETH worth of ETH to buy BCH
        # -1 ETH, +0.612798695395699 BCH
        AbstractTrade('ETH', 'BCH', 'ETH', 1),
    ]

    chart_data = {
        'BTC_ETH': {'weighted_average': 0.07420755},  # BTC/ETH
        'BTC_BCH': {'weighted_average': 0.12016601},  # BTC/BCH
        'ETH_BCH': {'weighted_average': 1.63185726},  # ETH/BCH
    }
    balances = {'BTC': 8}
    state = MarketState(chart_data, balances, datetime.now(), 'BTC')

    result = simulate_trades(trades, state)
    assert result == {
        'BCH': 0.612798695395699,
        'BTC': 6.89916995,
        'ETH': 13.834475063521165,
    }
