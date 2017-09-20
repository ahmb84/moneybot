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
            1318.21, 1250.1303170835492, 1321.0968779968252,
            1356.8537393818065, 1559.2033256779935, 1706.5783635178404,
            1943.7333059442003, 1926.3641924919414, 1938.5375993775979,
            2110.2941823943825, 1979.0441139804125, 2205.290992936024,
            2346.55877443037, 2447.8472640521254, 2509.782330100271,
            2414.3839478848113, 2394.3828888253765, 2774.9008718131163,
            2945.331557827161, 3316.2862344202244, 3713.6274925113707,
            3683.9559777577897, 4161.4867961475875, 4445.316900051991,
            4094.0740122250722, 4814.898649647468, 3471.510635368878,
            3344.5700857868314, 3531.7144842316757, 3655.9114903032564,
            3921.697412839387, 4021.9252482973607,
        ],
    ),
    (
        BuyHoldStrategy,
        [
            1318.21, 1250.13031708355, 1318.7913161977467, 1355.4680163728613,
            1560.7460389562796, 1706.55195924806, 1953.713405204591,
            2004.3384847938662, 1936.1100644061996, 2145.4571470699525,
            1971.147291869795, 2230.169902750859, 2384.125500051898,
            2429.566822557103, 2455.090289488733, 2397.813758618846,
            2403.6265170422535, 2797.565827157348, 2929.940361449671,
            3300.0259444946373, 3823.090786089592, 3898.9115251450953,
            4190.816447739185, 4435.932905372385, 3901.5635075237396,
            4713.817699090877, 3341.6512442396574, 3222.0600378136314,
            3393.648219399728, 3539.5292588239517, 3789.872845387461,
            3801.629029769423,
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
            2281.4522306052304, 2163.625371114985, 2286.4653846358556,
            2348.299064044728, 2698.448759524738, 2953.4321436149075,
            3363.6987947904736, 3333.6586465968758, 3354.894486735416,
            3652.2825702527894, 3424.9961109817245, 3816.512506873739,
            4060.992001663698, 4236.602205299198, 4340.008250196473,
            4170.917912689369, 4139.492996478755, 4797.9588578366875,
            5092.110140901915, 5733.866763885994, 6420.708132156658,
            6369.34352885316, 7193.13383872162, 7683.249047753546,
            7073.35006750934, 8318.93143743041, 5997.172708597952,
            5778.738109813539, 6101.838919939528, 6316.127689420455,
            6774.567195336466, 6946.904817627344,
        ],
    ),
    (
        BuyHoldStrategy,
        [
            2281.45223060523, 2317.0499607848997, 2429.3391474055197,
            2470.8600883043405, 2715.17561336956, 2768.86248610866,
            2725.1704172448, 2640.42775616256, 2677.4283762672003,
            2940.59048981456, 2817.1373396631398, 2996.7075568374903,
            2912.27522368995, 2857.1490418892404, 2968.9923699711,
            2911.83217355629, 2787.69019414464, 2969.5103522693403,
            3083.1196951368, 3483.975626956, 3495.3750496537305,
            3985.1330522320604, 4356.57432089736, 4486.514848231521,
            4648.159137124911, 5258.6576486863205, 4392.86233316611,
            4008.0401507829497, 4283.57294844856, 4424.4607555938,
            5002.44492499975, 4846.7819638171495,
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
