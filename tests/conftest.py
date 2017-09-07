# -*- coding: utf-8 -*-
import logging

import pytest
import staticconf
import yaml

import moneybot


TEST_CONFIG = """
trading:
  fiat: BTC
  interval: 86400
"""


@pytest.fixture(scope='session', autouse=True)
def config():
    staticconf.DictConfiguration(
        yaml.load(TEST_CONFIG),
        namespace=moneybot.CONFIG_NS,
    )
    logging.basicConfig(level=logging.INFO)
