# -*- coding: utf-8 -*-
import logging
from argparse import ArgumentParser

from moneybot import config
from moneybot import load_config
from moneybot.examples.strategies import BuffedCoinStrategy
from moneybot.examples.strategies import BuyHoldStrategy
from moneybot.examples.strategies import PeakRiderStrategy
from moneybot.fund import Fund
from moneybot.market.adapters.poloniex import PoloniexMarketAdapter
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
    # TODO: Shouldn't be necessary to provide initial balances for live trading
    adapter = PoloniexMarketAdapter(
        fiat,
        MarketHistory(),
        {},  # Actual balances will be fetched from Poloniex
    )
    fund = Fund(strategy, adapter)

    if args.force_rebalance is True:
        confirm = input('Are you sure you want to rebalance your fund? [y/N] ')
        if confirm.strip().lower() == 'y':
            fund.force_rebalance_next_step = True
    fund.run_live()


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

    parser.add_argument(
        '--force-rebalance',
        action='store_true',
        help='Equalize value held in all available coins before starting to live trade',
    )

    args = parser.parse_args()
    logging.getLogger().setLevel(args.log_level)
    main(args)
