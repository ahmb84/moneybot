# -*- coding: utf-8 -*-
import logging
from unittest.mock import patch

from pytest import fixture
from pyloniex import PoloniexPrivateAPI


logging.basicConfig(level=logging.INFO)


@fixture(scope='session', autouse=True)
def poloniex_private():
    dummy = PoloniexPrivateAPI(key='polo key', secret='polo secret')
    with patch('moneybot.clients.Poloniex.get_private', return_value=dummy):
        yield dummy
