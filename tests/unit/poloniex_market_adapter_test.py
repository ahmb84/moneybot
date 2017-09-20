# -*- coding: utf-8 -*-
from datetime import datetime
from unittest.mock import call
from unittest.mock import patch

import pytest
from pyloniex.constants import OrderType

from moneybot.errors import InsufficientBalanceError
from moneybot.errors import NoMarketAvailableError
from moneybot.errors import OrderTooSmallError
from moneybot.market import Order
from moneybot.market.adapters.poloniex import PoloniexMarketAdapter
from moneybot.market.state import MarketState
from moneybot.testing import MarketHistoryMock
from moneybot.trade import AbstractTrade


@pytest.fixture
def market_adapter():
    return PoloniexMarketAdapter('BTC', MarketHistoryMock(), {})


@pytest.fixture
def market_state():
    chart_data = {
        'BTC_ETH': {'weighted_average': 0.07420755},  # BTC/ETH
        'BTC_BCH': {'weighted_average': 0.12016601},  # BTC/BCH
        'ETH_BCH': {'weighted_average': 1.63185726},  # ETH/BCH
    }
    return MarketState(chart_data, {}, datetime.now(), 'BTC')


@pytest.mark.parametrize('trade,expected', [
    (
        AbstractTrade('BTC', 'ETH', 'ETH', 4),
        [
            Order(
                'BTC_ETH',
                0.07420755,
                4,
                Order.Direction.BUY,
                OrderType.fill_or_kill,
            ),
        ],
    ),
    (
        AbstractTrade('BTC', 'ETH', 'BTC', 0.5),
        [
            Order(
                'BTC_ETH',
                0.07420755,
                6.737858883631113,
                Order.Direction.BUY,
                OrderType.fill_or_kill,
            ),
        ],
    ),
    (
        AbstractTrade('ETH', 'BTC', 'BCH', 3.14),
        [
            Order(
                'BTC_ETH',
                0.07420755,
                5.124031796400001,
                Order.Direction.SELL,
                OrderType.fill_or_kill,
            ),
        ],
    ),
])
def test_reify_trade(market_state, trade, expected):
    orders = PoloniexMarketAdapter.reify_trade(trade, market_state)
    assert orders == expected


def test_reify_trade_no_market(market_state):
    # Don't have a market for this one
    trade = AbstractTrade('BTC', 'WAT', 'BTC', 1.4)
    with pytest.raises(NoMarketAvailableError):
        PoloniexMarketAdapter.reify_trade(trade, market_state)


def test_reify_trades(market_state):
    trades = [
        AbstractTrade('BTC', 'ETH', 'ETH', 4),
        AbstractTrade('BTC', 'ETH', 'BTC', 0.5),
        AbstractTrade('ETH', 'BTC', 'BCH', 3.14),
        AbstractTrade('BTC', 'WAT', 'BTC', 1.4),
    ]
    orders = PoloniexMarketAdapter.reify_trades(trades, market_state)
    assert orders == [
        Order(
            'BTC_ETH',
            0.07420755,
            4,
            Order.Direction.BUY,
            OrderType.fill_or_kill,
        ),
        Order(
            'BTC_ETH',
            0.07420755,
            6.737858883631113,
            Order.Direction.BUY,
            OrderType.fill_or_kill,
        ),
        Order(
            'BTC_ETH',
            0.07420755,
            5.124031796400001,
            Order.Direction.SELL,
            OrderType.fill_or_kill,
        ),
    ]


@pytest.mark.parametrize('order,balances', [
    (
        Order(
            'BTC_ETH',
            0.07420755,
            2,
            Order.Direction.BUY,
            OrderType.fill_or_kill,
        ),
        {'BTC': 1},
    ),
    (
        Order(
            'BTC_ETH',
            0.07420755,
            2,
            Order.Direction.SELL,
            OrderType.fill_or_kill,
        ),
        {'ETH': 3},
    ),
])
def test_validate_order(order, balances):
    PoloniexMarketAdapter.validate_order(order, balances)


@pytest.mark.parametrize('order,balances,error', [
    (
        Order(
            'BTC_ETH',
            0.07420755,
            0,
            Order.Direction.BUY,
            OrderType.fill_or_kill,
        ),
        {},
        OrderTooSmallError,
    ),
    (
        Order(
            'BTC_ETH',
            0.07420755,
            0,
            Order.Direction.SELL,
            OrderType.fill_or_kill,
        ),
        {},
        OrderTooSmallError,
    ),
    (
        Order(
            'BTC_ETH',
            0.07420755,
            1,
            Order.Direction.BUY,
            OrderType.fill_or_kill,
        ),
        {},
        InsufficientBalanceError,
    ),
    (
        Order(
            'BTC_ETH',
            0.07420755,
            1,
            Order.Direction.SELL,
            OrderType.fill_or_kill,
        ),
        {},
        InsufficientBalanceError,
    ),
    (
        Order(
            'BTC_ETH',
            0.07420755,
            1,
            Order.Direction.BUY,
            OrderType.fill_or_kill,
        ),
        {'BTC': 0.001},
        InsufficientBalanceError,
    ),
    (
        Order(
            'BTC_ETH',
            0.07420755,
            1,
            Order.Direction.SELL,
            OrderType.fill_or_kill,
        ),
        {'ETH': 0.001},
        InsufficientBalanceError,
    ),
])
def test_validate_order_error(order, balances, error):
    with pytest.raises(error):
        PoloniexMarketAdapter.validate_order(order, balances)


def test_execute_order_buy(market_adapter):
    order = Order(
        'BTC_ETH',
        0.07420755,
        2,
        Order.Direction.BUY,
        OrderType.fill_or_kill,
    )

    balances = {'BTC': {'available': '1'}}
    response = {'orderNumber': 12345, 'resultingTrades': []}
    with patch.object(market_adapter.private_api, 'return_complete_balances', return_value=balances):
        with patch.object(market_adapter.private_api, 'buy', return_value=response) as mock_buy:
            order_id = market_adapter.execute_order(order)

    assert order_id == 12345

    mock_buy.assert_called_once_with(
        currency_pair=order.market,
        rate=order.price,
        amount=order.amount,
        order_type=order.type,
    )


def test_execute_order_buy_retry(market_adapter):
    order = Order(
        'BTC_ETH',
        0.07420755,
        2,
        Order.Direction.BUY,
        OrderType.fill_or_kill,
    )

    balances = {'BTC': {'available': '1'}}
    responses = [
        {'error': 'Unable to fill order completely.'},
        {'orderNumber': 12345, 'resultingTrades': []},
    ]
    with patch.object(market_adapter.private_api, 'return_complete_balances', return_value=balances):
        with patch.object(market_adapter.private_api, 'buy', side_effect=responses) as mock_buy:
            order_id = market_adapter.execute_order(order)

    assert order_id == 12345

    mock_buy.assert_has_calls([
        call(
            currency_pair=order.market,
            rate=order.price,
            amount=order.amount,
            order_type=order.type,
        ),
        call(
            currency_pair=order.market,
            rate=order.price + PoloniexMarketAdapter.ORDER_ADJUSTMENT,
            amount=order.amount,
            order_type=order.type,
        ),
    ])


def test_execute_order_sell(market_adapter):
    order = Order(
        'BTC_ETH',
        0.07420755,
        2,
        Order.Direction.SELL,
        OrderType.fill_or_kill,
    )

    balances = {'ETH': {'available': '4'}}
    response = {'orderNumber': 67890, 'resultingTrades': []}
    with patch.object(market_adapter.private_api, 'return_complete_balances', return_value=balances):
        with patch.object(market_adapter.private_api, 'sell', return_value=response) as mock_sell:
            order_id = market_adapter.execute_order(order)

    assert order_id == 67890

    mock_sell.assert_called_once_with(
        currency_pair=order.market,
        rate=order.price,
        amount=order.amount,
        order_type=order.type,
    )


def test_execute_order_sell_retry(market_adapter):
    order = Order(
        'BTC_ETH',
        0.07420755,
        2,
        Order.Direction.SELL,
        OrderType.fill_or_kill,
    )

    balances = {'ETH': {'available': '4'}}
    responses = [
        {'error': 'Unable to fill order completely.'},
        {'orderNumber': 67890, 'resultingTrades': []},
    ]
    with patch.object(market_adapter.private_api, 'return_complete_balances', return_value=balances):
        with patch.object(market_adapter.private_api, 'sell', side_effect=responses) as mock_sell:
            order_id = market_adapter.execute_order(order)

    assert order_id == 67890

    mock_sell.assert_has_calls([
        call(
            currency_pair=order.market,
            rate=order.price,
            amount=order.amount,
            order_type=order.type,
        ),
        call(
            currency_pair=order.market,
            rate=order.price - PoloniexMarketAdapter.ORDER_ADJUSTMENT,
            amount=order.amount,
            order_type=order.type,
        ),
    ])


def test_execute_order_retries_exhausted(market_adapter):
    order = Order(
        'BTC_ETH',
        0.07420755,
        2,
        Order.Direction.BUY,
        OrderType.fill_or_kill,
    )

    balances = {'BTC': {'available': '1'}}
    responses = [
        {'error': 'Unable to fill order completely.'},
        {'orderNumber': 67890, 'resultingTrades': []},
    ]
    with patch.object(market_adapter.private_api, 'return_complete_balances', return_value=balances):
        with patch.object(market_adapter.private_api, 'buy', side_effect=responses) as mock_buy:
            order_id = market_adapter.execute_order(order, attempts=1)

    assert order_id is None

    mock_buy.assert_called_once_with(
        currency_pair=order.market,
        rate=order.price,
        amount=order.amount,
        order_type=order.type,
    )


def test_execute_order_invalid(market_adapter):
    order = Order(
        'BTC_ETH',
        0.07420755,
        2,
        Order.Direction.BUY,
        OrderType.fill_or_kill,
    )

    balances = {}
    with patch.object(market_adapter.private_api, 'return_complete_balances', return_value=balances):
        order_id = market_adapter.execute_order(order)

    assert order_id is None


def test_execute_order_unknown_error(market_adapter):
    order = Order(
        'BTC_ETH',
        0.07420755,
        2,
        Order.Direction.BUY,
        OrderType.fill_or_kill,
    )

    balances = {'BTC': {'available': '1'}}
    response = {'error': 'You are a bad person and you should feel bad.'}
    with patch.object(market_adapter.private_api, 'return_complete_balances', return_value=balances):
        with patch.object(market_adapter.private_api, 'buy', return_value=response):
            order_id = market_adapter.execute_order(order)

    assert order_id is None
