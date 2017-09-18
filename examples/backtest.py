# -*- coding: utf-8 -*-
import logging
from argparse import ArgumentParser

from moneybot import config
from moneybot import load_config
from moneybot.evaluate import evaluate
from moneybot.examples.strategies import BuffedCoinStrategy
from moneybot.examples.strategies import BuyHoldStrategy
from moneybot.examples.strategies import PeakRiderStrategy
from moneybot.fund import Fund
from moneybot.market.adapters.backtest import BacktestMarketAdapter
from moneybot.market.history import MarketHistory


strategies = {
    'buffed-coin': BuffedCoinStrategy,
    'buy-hold': BuyHoldStrategy,
    'peak-rider': PeakRiderStrategy,
}


def main(args):
    load_config(args.config)
    fiat = config.read_string('trading.fiat')

    strategy = strategies[args.strategy](
        fiat,
        config.read_int('trading.interval'),
    )
    adapter = BacktestMarketAdapter(
        fiat,
        MarketHistory(),
        {'BTC': 1.0},
    )
    fund = Fund(strategy, adapter)

    summary = evaluate(
        fund,
        '2017-01-01',
        '2017-06-29',
        duration_days=30,
        window_distance_days=14,
    )

    print(summary)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument(
        '-c', '--config',
        default='config-example.yml',
        type=str,
        help='path to config file',
    )
    parser.add_argument(
        '-l', '--log-level',
        default='INFO',
        type=str,
        choices=['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Python logging level',
    )
    parser.add_argument(
        '-s', '--strategy',
        default='buffed-coin',
        type=str,
        choices=strategies.keys(),
    )

    args = parser.parse_args()
    logging.getLogger().setLevel(args.log_level)
    main(args)
