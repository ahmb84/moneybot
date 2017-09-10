# -*- coding: utf-8 -*-
from datetime import datetime
from logging import getLogger
from time import sleep
from time import time
from typing import Generator
from copy import deepcopy

import pandas as pd
from pyloniex.errors import PoloniexServerError

from moneybot.market.adapters import MarketAdapter
from moneybot.strategy import Strategy


logger = getLogger(__name__)


class Fund:
    '''
    Funds are the MoneyBot's highest level abstraction.
    Funds have a Strategy, which proposes trades to
    their MarketAdapter.

    There are two ways for a Fund to run: live, or in a backtest.

       my_fund.run_live()

    or

       my_fund.begin_backtest(start, end)

    In both cases, the fund executes its private method `step(time)`
    repeatedly. Strategies decide their own trading interval; this
    dictates the temporal spacing between a fund's steps.
    '''

    def __init__(self, strategy: Strategy, adapter: MarketAdapter) -> None:
        self.strategy = strategy
        # MarketAdapter executes trades, fetches balances
        self.market_adapter = adapter
        # MarketHistory stores historical market data
        self.market_history = adapter.market_history

    def rebalance(self) -> float:
        """Reset the fund to a value-balanced state, i.e. we hold an equal
        value (measured in fiat) of every coin available to us.
        """
        logger.info('Resetting fund')

        now = datetime.now()
        market_state = self.market_adapter.get_market_state(now)
        proposed_trades = self.strategy.propose_trades_for_total_rebalancing(market_state)
        if proposed_trades:
            self.market_adapter.filter_and_execute(proposed_trades)

        usd_val = self.market_adapter.market_state.estimate_total_value_usd()
        logger.info(f'Est. USD value: {usd_val}')
        return usd_val

    def step(self, time: datetime) -> float:
        # We make a copy of our MarketAdapter's market_state
        # This way, we can pass the copy to Strategy.propose_trades()
        # without having to worry about the strategy mutating the market_state
        # to pull some sort of shennannigans (even accidentally).
        # This way, the Strategy cannot communicate at all with the MarketAdapter
        # except through ProposedTrades.
        market_state = self.market_adapter.get_market_state(time)
        copied_market_state = deepcopy(market_state)
        # print('market_state.balances', market_state.balances)
        # Now, propose trades. If you're writing a strategy, you will implement this method.
        proposed_trades = self.strategy.propose_trades(copied_market_state, self.market_history)
        # If the strategy proposed any trades,
        if proposed_trades:
            # the MarketAdapter will execute them.
            # If we're backtesting, these trades won't really happen.
            # If we're trading for real, we will attempt to execute the proposed trades
            # at the best price we can.
            # In either case, this method is side-effect-y;
            # it sets MarketAdapter.balances, after all trades have been executed.
            self.market_adapter.filter_and_execute(proposed_trades)
        # print('market_adapter.balances after propose_trades()', # self.market_adapter.balances)
        # Finally, we get the USD value of our whole fund,
        # now that all trades (if there were any) have been executed.
        usd_value = self.market_adapter.market_state.estimate_total_value_usd()
        return usd_value

    def run_live(self):
        period = self.strategy.trade_interval
        logger.info(f'Live trading with {period} seconds between steps')

        while True:
            step_start = time()
            cur_dt = datetime.now()
            try:
                # Before anything, get freshest data from Poloniex
                self.market_history.scrape_latest()
                # Now the fund can step()
                logger.info(f'Fund::step({cur_dt})')
                usd_val = self.step(cur_dt)
                # After its step, we have got the USD value.
                logger.info(f'Est. USD value: {usd_val}')
            except PoloniexServerError:
                logger.exception(
                    'Received server error from Poloniex; sleeping until next step'
                )

            # Wait until our next time to run, accounting for the time taken by
            # this step to run
            step_time = time() - step_start
            sleep_time = (period - step_time) % period
            logger.debug(f'Trading step took {step_time} seconds')
            logger.debug(f'Sleeping {sleep_time} seconds until next step')
            sleep(sleep_time)

    def begin_backtest(
        self,
        start_time: str,
        end_time: str,
    ) -> Generator[float, None, None]:
        '''
        Takes a start time and end time (as parse-able date strings).

        Returns a generator over a list of USD values for each point (trade
        interval) between start and end.
        '''
        # MarketAdapter executes trades
        # Set up the historical coinstore
        # A series of trade-times to run each of our strategies through.
        dates = pd.date_range(
            pd.Timestamp(start_time),
            pd.Timestamp(end_time),
            freq=f'{self.strategy.trade_interval}S',
        )
        for date in dates:
            val = self.step(date)
            yield val
