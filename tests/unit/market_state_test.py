# -*- coding: utf-8 -*-
from datetime import datetime

import pytest

from moneybot.market.state import MarketState


@pytest.fixture
def state():
    chart_data = {
        'BTC_ETH': {'weighted_average': 0.07096974},
        'ETH_BCH': {'weighted_average': 1.84201100},
    }
    balances = {}
    return MarketState(chart_data, balances, datetime.now(), 'BTC')


def test_estimate_value(state):
    # First, a sanity check
    assert state.estimate_value('BTC', 1.0, 'BTC') == 1.0

    # How much BTC is 2.5 ETH worth?
    assert state.estimate_value('ETH', 2.5, 'BTC') == 0.17742435

    # How much ETH is 1 BTC worth?
    assert state.estimate_value('BTC', 1.0, 'ETH') == 14.09051237893784

    # How much ETH is 4.2 BCH worth?
    assert state.estimate_value('BCH', 4.2, 'ETH') == 7.7364462000000005

    # How much BCH is 2.4 ETH worth?
    assert state.estimate_value('ETH', 2.4, 'BCH') == 1.302923815330093

    # Last, try a combination we know nothing about
    assert state.estimate_value('ETH', 1.0, 'XRP') is None


def test_estimate_values(state):
    balances = {
        'BTC': 8.3,
        'ETH': 7.6,
        'XRP': 4.9,
    }
    assert state.estimate_values(balances, 'BTC') == {
        'BTC': 8.3,
        'ETH': 0.539370024,
        'XRP': 0,
    }
