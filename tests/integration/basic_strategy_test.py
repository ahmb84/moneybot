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
            1318.21, 1250.130317083549, 1321.1059287022097, 1356.8335823380767,
            1559.149640854199, 1706.548155760149, 1943.7351973573993,
            1926.3812897199732, 1938.6633590470162, 2110.4587154016817,
            1979.2199596302594, 2205.460015576339, 2346.9629666067153,
            2448.355308432767, 2510.263137863438, 2414.877395691592,
            2395.2923569312925, 2776.198763798655, 2946.7942355684154,
            3317.8693490698774, 3715.317351593903, 3679.9501420745632,
            4157.468339137907, 4442.2473245380725, 4090.3230041227503,
            4809.986216794976, 3467.0602018818668, 3334.765963553269,
            3521.9398683456952, 3643.6811560714414, 3903.084595368637,
            4002.020499979611,
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
            2281.4522306052304, 2163.625371114985, 2286.4642719319736,
            2348.298831737953, 2698.4512528156774, 2953.375825638561,
            3363.455520504497, 3333.427169558423, 3354.6305882086244,
            3652.029711369097, 3424.7403576964766, 3816.389395532299,
            4061.151205223887, 4236.6508401775845, 4343.76441607497,
            4178.730289906624, 4144.781858795589, 4803.907594226465,
            5098.986280561512, 5741.079003103908, 6428.88663434668,
            6377.309841367008, 7204.350585567969, 7695.839810116442,
            7087.624751351982, 8335.427105556857, 6009.7445641199265,
            5779.3523093841, 6103.5384337579835, 6314.862772024179,
            6769.13182110582, 6940.7018617924505,
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
