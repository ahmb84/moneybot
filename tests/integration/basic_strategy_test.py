# -*- coding: utf-8 -*-
import pytest
from pandas import Timestamp

from moneybot.examples.strategies import BuffedCoinStrategy
from moneybot.examples.strategies import BuyHoldStrategy
from moneybot.fund import Fund
from moneybot.testing import MarketHistoryMock
from moneybot.market.adapters.backtest import BacktestMarketAdapter


def test_strategy_step():
    """Strategies can step forward.
    """
    fiat = 'BTC'
    today = Timestamp('2017-05-01')

    initial_balances = {fiat: 1.0}

    strategy = BuffedCoinStrategy(fiat, 86400)
    adapter = BacktestMarketAdapter(
        fiat,
        MarketHistoryMock(),
        initial_balances,
    )
    fund = Fund(strategy, adapter)

    new_value = fund.step(today)
    assert new_value == 1318.21


@pytest.mark.xfail(
    reason=(
        'For unknown reason(s), the two funds end up with the same value '
        'regardless of whether they rebalance'
    ),
)
def test_strategy_force_rebalance():
    """Strategies can force a rebalance by passing `force_rebalance=True` into
    `Fund::step`.
    """
    fiat = 'BTC'
    start = '2017-05-01'
    end = '2017-05-20'

    initial_balances = {fiat: 100, 'ETH': 3141.5926, 'XRP': 500}
    strategy = BuffedCoinStrategy(fiat, 86400)

    adapter_a = BacktestMarketAdapter(
        fiat,
        MarketHistoryMock(),
        initial_balances.copy(),
    )
    fund_a = Fund(strategy, adapter_a)

    adapter_b = BacktestMarketAdapter(
        fiat,
        MarketHistoryMock(),
        initial_balances.copy(),
    )
    fund_b = Fund(strategy, adapter_b)

    # First we'll run a backtest on *both* funds, and see that the final values
    # are what we expect
    results_a = list(fund_a.run_backtest(start, end))
    results_b = list(fund_b.run_backtest(start, end))
    assert results_a[-1] == 945757.92
    assert results_b[-1] == 945757.92

    ts = Timestamp('2017-06-01')

    # Fund A steps without a rebalance, while B *does* rebalance
    value_without_rebalance = fund_a.step(ts, force_rebalance=False)
    value_with_rebalance = fund_b.step(ts, force_rebalance=True)
    assert value_without_rebalance != value_with_rebalance


@pytest.mark.parametrize('strategy_cls,expected', [
    (
        BuffedCoinStrategy,
        [
            1318.21, 1250.13, 1321.11, 1356.83, 1559.15, 1706.55, 1943.74,
            1926.38, 1938.66, 2110.46, 1979.22, 2205.46, 2346.96, 2448.36,
            2510.26, 2414.88, 2395.29, 2776.2, 2946.79, 3317.87, 3715.32,
            3679.95, 4157.47, 4442.25, 4090.32, 4809.99, 3467.06, 3334.77,
            3521.94, 3643.68, 3903.08, 4002.02,
        ],
    ),
    (
        BuyHoldStrategy,
        [
            1318.21, 1250.13, 1318.79, 1355.47, 1560.75, 1706.55, 1953.71,
            2004.34, 1936.11, 2145.46, 1971.15, 2230.17, 2384.13, 2429.57,
            2455.09, 2397.81, 2403.63, 2797.57, 2929.94, 3300.03, 3823.09,
            3898.91, 4190.82, 4435.93, 3901.56, 4713.82, 3341.65, 3222.06,
            3393.65, 3539.53, 3789.87, 3801.63,
        ],
    ),
])
def test_strategy_fiat_only_initial_balance(strategy_cls, expected):
    """Strategies should produce their expected values when starting with a
    fiat-only portfolio.
    """
    fiat = 'BTC'
    start = '2017-05-01'
    end = '2017-06-01'

    initial_balances = {fiat: 1.0}

    strategy = strategy_cls(fiat, 86400)
    adapter = BacktestMarketAdapter(
        fiat,
        MarketHistoryMock(),
        initial_balances,
    )
    fund = Fund(strategy, adapter)

    results = list(fund.run_backtest(start, end))
    assert results == expected


@pytest.mark.parametrize('strategy_cls,expected', [
    (
        BuffedCoinStrategy,
        [
            2281.45, 2163.63, 2286.46, 2348.3, 2698.45, 2953.38, 3363.46,
            3333.43, 3354.63, 3652.03, 3424.74, 3816.39, 4061.15, 4236.65,
            4343.76, 4178.73, 4144.78, 4803.91, 5098.99, 5741.08, 6428.89,
            6377.31, 7204.35, 7695.84, 7087.62, 8335.43, 6009.74, 5779.35,
            6103.54, 6314.86, 6769.13, 6940.7,
        ],
    ),
    (
        BuyHoldStrategy,
        [
            2281.45, 2317.05, 2429.34, 2470.86, 2715.18, 2768.86, 2725.17,
            2640.43, 2677.43, 2940.59, 2817.14, 2996.71, 2912.28, 2857.15,
            2968.99, 2911.83, 2787.69, 2969.51, 3083.12, 3483.98, 3495.38,
            3985.13, 4356.57, 4486.51, 4648.16, 5258.66, 4392.86, 4008.04,
            4283.57, 4424.46, 5002.44, 4846.78,
        ],
    ),
])
def test_strategies_mixed_initial_balance(strategy_cls, expected):
    """Strategies should produce their expected values when starting with a
    mixed portfolio.
    """
    fiat = 'BTC'
    start = '2017-05-01'
    end = '2017-06-01'

    initial_balances = {fiat: 1.0, 'ETH': 12.3, 'XRP': 5.3, 'LTC': 0.5}

    strategy = strategy_cls(fiat, 86400)
    adapter = BacktestMarketAdapter(
        fiat,
        MarketHistoryMock(),
        initial_balances,
    )
    fund = Fund(strategy, adapter)

    results = list(fund.run_backtest(start, end))
    assert results == expected
