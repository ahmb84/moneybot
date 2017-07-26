# -*- coding: utf-8 -*-
import pytest

from moneybot import config
from moneybot.examples.strategies import BuffedCoinStrategy
from moneybot.examples.strategies import BuyHoldStrategy
from moneybot.examples.strategies import PeakRiderStrategy
from moneybot.fund import Fund
from moneybot.testing import MarketHistoryMock
from moneybot.market.adapters.backtest import BacktestMarketAdapter


@pytest.fixture
def expected_results():
    """Each strategy, and the USD values it should produce after each step
    through the series of trade-times.
    """
    return [
        {
            'strategy': BuffedCoinStrategy,
            'values': [
                1318.21, 1250.13, 1318.79, 1355.47, 1560.75, 1694.85, 1918.27,
                1866.54, 1888.66, 2039.06, 1967.42, 2184.11, 2326.3, 2461.91,
                2589.18, 2544.36, 2420.49, 2778.22, 2958.32, 3313.64, 3686.43,
                3704.98, 4091.39, 4395.39, 4085.4, 4770.42, 3487.72, 3384.36,
                3546.08, 3664.02, 3820.51, 3976.37
            ],
        },
        {
            'strategy': BuyHoldStrategy,
            'values': [
                1318.21, 1250.13, 1318.79, 1355.47, 1560.75, 1706.55, 1953.71,
                2004.34, 1936.11, 2145.46, 1971.15, 2230.17, 2384.13, 2429.57,
                2455.09, 2397.81, 2403.63, 2797.57, 2929.94, 3300.03, 3823.09,
                3898.91, 4190.82, 4435.93, 3901.56, 4713.82, 3341.65, 3222.06,
                3393.65, 3539.53, 3789.87, 3801.63,
            ],
        },
        {
            'strategy': PeakRiderStrategy,
            'values': [
                1318.21, 1250.13, 1318.79, 1355.47, 1560.75, 1706.55, 1920.65,
                1889.18, 1906.54, 2071.08, 1947.65, 2156.81, 2296.88, 2381.47,
                2439.71, 2317.35, 2315.89, 2593.93, 2707.41, 2988.51, 3172.41,
                3208.15, 3549.13, 3715.67, 3672.46, 4213.29, 3301.56, 3016.65,
                3196.71, 3241.07, 3325.59, 3354.02,
            ],
        },
    ]


def test_strategies(expected_results):
    '''
    Strategies should produce their expected values
    '''
    # The start and end of our test period
    start = '2017-05-01'
    end = '2017-06-01'
    fiat = config.read_string('trading.fiat')
    interval = config.read_int('trading.interval')

    for expected in expected_results:
        strategy = expected['strategy'](fiat, interval)
        adapter = BacktestMarketAdapter(
            MarketHistoryMock(),
            {'BTC': 1.0},
            fiat,
        )
        fund = Fund(strategy, adapter)
        res = list(fund.begin_backtest(start, end))
        # print(res)
        assert res == expected['values']


def test_all_results_diff(expected_results):
    '''
    No two results should be equal.
    '''
    for i, expected in enumerate(expected_results[:-1]):
        assert expected != expected_results[i + 1]
