# -*- coding: utf-8 -*-
from logging import getLogger
from typing import List
from typing import Iterable

from numpy import mean
from pandas import date_range
from pandas import Series
from pandas import Timestamp

from moneybot.fund import Fund


logger = getLogger(__name__)


def roi(values: List[float]) -> float:
    return (values[-1] - values[0]) / values[0]


def max_drawdown(values: List[float]) -> float:
    maximum = max(values)
    idxmax = values.index(maximum)
    subsequent = values[idxmax:]
    return (maximum - min(subsequent)) / maximum


def sterling_ratio(
    many_values: List[List[float]],
    days_per_simulation: int,
    risk_free_rate: float = 0.0091,
) -> float:
    rate_per_day = risk_free_rate / 90
    adjusted_rate = rate_per_day * days_per_simulation
    rs = [roi(v) for v in many_values]
    max_drawdowns = list(map(max_drawdown, many_values))
    return (mean(rs) - adjusted_rate) / mean(max_drawdowns)


# # return over max drawdown
# def RoMaD (values):
#     my_roi = roi(values)
#     max_dd = max_drawdown(values)
#     if max_dd != 0:
#         return  my_roi / max_dd
#     return my_roi


def summary(
    many_values: List[List[float]],
    days_per_simulation: int,
) -> Series:
    rois = Series([roi(values) for values in many_values])
    rois_desc = rois.describe()
    rois_desc['sterling_ratio'] = sterling_ratio(many_values, days_per_simulation)
    return rois_desc


def backtests(
        fund: Fund,
        start_times: List[str]
) -> Iterable[List[float]]:
    for i, start_time in enumerate(start_times[:-1]):
        end_time = start_times[i + 1]
        logger.info(f'Testing from {start_time} to {end_time}')
        yield list(fund.run_backtest(start_time, end_time))


def evaluate(
    fund: Fund,
    start_date: str,
    end_date: str,
    duration_days: int = 90,
    window_distance_days: int = 30,
) -> Series:
    start = Timestamp(start_date)
    end = Timestamp(end_date)
    start_times = date_range(start, end, freq='{!s}d'.format(window_distance_days))
    backtest_results = list(backtests(fund, start_times))
    return summary(backtest_results, duration_days)
