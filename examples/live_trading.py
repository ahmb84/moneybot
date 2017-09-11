# -*- coding: utf-8 -*-
import logging
from argparse import ArgumentParser

from moneybot import config
from moneybot import load_config
from moneybot.examples.strategies import BuffedCoinStrategy
from moneybot.examples.strategies import BuyHoldStrategy
from moneybot.examples.strategies import PeakRiderStrategy
from moneybot.fund import Fund
from moneybot.market.adapters.live import LiveMarketAdapter
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
    adapter = LiveMarketAdapter(MarketHistory(), fiat)

    fund = Fund(strategy, adapter)

    # TODO
    # if args.force_rebalance is True:
    #     confirm = input('Are you sure you want to rebalance your fund? [y/N] ')
    #     if confirm.strip().lower() == 'y':
    #         fund.rebalance()
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
