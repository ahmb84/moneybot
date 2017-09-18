# -*- coding: utf-8 -*-
import pytest

from pandas import Timestamp

from moneybot.examples.strategies import BuffedCoinStrategy
from moneybot.examples.strategies import BuyHoldStrategy
from moneybot.fund import Fund
from moneybot.testing import MarketHistoryMock
from moneybot.market.adapters.backtest import BacktestMarketAdapter

'''
Fund method tests
'''


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


def test_strategy_force_rebalacne():
    """Strategies can force a rebalance
    by passing `force_rebalance=True`
    into `Fund::step`
    """
    fiat = 'BTC'
    start = '2017-05-01'
    end = '2017-05-30'

    initial_balances = {fiat: 1.0}

    strategy = BuffedCoinStrategy(fiat, 86400)
    adapter = BacktestMarketAdapter(
        fiat,
        MarketHistoryMock(),
        initial_balances,
    )
    fund = Fund(strategy, adapter)

    # First we'll run a backtest, and see that the latest value is what we expect
    results = list(fund.run_backtest(start, end))
    assert results[-1] == 3551.63

    # Now, if we do one more step,
    # but force a rebalance for it,
    # the following value should *not* be what we expect
    new_value = fund.step(Timestamp('2017-06-01'), force_rebalance=True)
    # If we had NOT rebalanced,
    # The value here would have been
    #   3801.01
    # Instead, we should see some other value:
    assert new_value == 3851.61


'''
Integration tests
'''


@pytest.mark.parametrize('strategy_cls,expected', [
    (
        BuffedCoinStrategy,
        [
            1318.21, 1250.13, 1327.42, 1357.88, 1554.3, 1690.92, 1911.72,
            1866.52, 1897.17, 2059.47, 1947.44, 2171.59, 2278.7, 2384.52,
            2477.85, 2384.51, 2362.72, 2712.39, 2876.84, 3236.44, 3592.33,
            3565.5, 4049.89, 4337.58, 3996.98, 4704.23, 3391.88, 3229.91,
            3411.23, 3551.63, 3801.01, 3924.06,
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
            2281.45, 2166.24, 2299.17, 2351.69, 2691.87, 2928.51, 3311.15,
            3232.9, 3285.88, 3567.05, 3372.98, 3761.2, 3947.1, 4130.37,
            4292.01, 4130.27, 4092.48, 4698.07, 4982.92, 5605.78, 6222.19,
            6175.71, 7014.71, 7513.04, 6923.04, 8148.01, 5874.96, 5594.41,
            5908.44, 6151.62, 6583.48, 6796.62,
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
