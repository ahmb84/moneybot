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
        # A boolean the caller can set
        # to force a rebalance on the next trading step
        # (after that rebalance, this will be reset to `False`)
        self.force_rebalance_next_step = False

    def step(
        self,
        time: datetime,
        force_rebalance: bool = False,
    ) -> float:
        self.market_adapter.update_market_state(time)
        # Copy MarketState to prevent mutation by the Strategy (even
        # accidentally). The Strategy's sole means of communication with the
        # MarketAdapter and Fund is the list of ProposedTrades it creates.
        # TODO: Make this unnecessary, either by making MarketState immutable
        # or by other means.
        market_state = deepcopy(self.market_adapter.market_state)

        if force_rebalance is True:
            proposed_trades = self.strategy.propose_trades_for_total_rebalancing(market_state)
        else:
            # Generally, the Strategy decides when to rebalance. If you're
            # writing your own, this is the method you'll implement!
            proposed_trades = self.strategy.propose_trades(
                market_state,
                self.market_history,
            )

        if proposed_trades:
            # We "reify" (n. make (something abstract) more concrete or real)
            # our proposed AbstractTrades to produce Orders that our
            # MarketAdapter actually knows how to execute.
            orders = self.market_adapter.reify_trades(
                proposed_trades,
                market_state,
            )
            logger.debug(
                f'Attempting to execute {len(orders)} orders based on '
                f'{len(proposed_trades)} proposed trades'
            )
            successful_order_ids = []
            for order in orders:
                # Each concrete subclass of MarketAdapter decides what it means
                # to execute an order. For example, PoloniexMarketAdapter
                # actually sends requests to Poloniex's trading API, but
                # BacktestMarketAdapter just mutates some of its own internal
                # state.
                #
                # In general we don't want this to be side-effect-y, so the way
                # BacktestMarketAdapter is a little gross. We should try to fix
                # that.
                #
                # MarketAdapter::execute_order returns an Optional[int] that we
                # currently ignore: an order identifier if the execution was
                # "successful" (whatever that means for the adapter subclass),
                # or None otherwise.
                order_id = self.market_adapter.execute_order(order)
                if order_id is not None:
                    successful_order_ids.append(order_id)
            logger.info(
                f'{len(successful_order_ids)} of {len(orders)} orders '
                'executed successfully'
            )

        # After the dust has settled, we update our view of the market state.
        self.market_adapter.update_market_state(time)

        # Finally, return the aggregate USD value of our fund.
        return self.market_adapter.market_state.estimate_total_value_usd(
            self.market_adapter.market_state.balances,
        )

    def run_live(self):
        period = self.strategy.trade_interval
        logger.info(f'Live trading with {period} seconds between steps')

        while True:
            step_start = time()
            cur_dt = datetime.now()
            try:
                # Before anything, get freshest data from Poloniex
                self.market_history.scrape_latest()
                logger.info(f'Fund::step({cur_dt})')
                # The caller can "queue up" a force rebalance for the next
                # trading step.
                usd_val = self.step(
                    cur_dt,
                    force_rebalance=self.force_rebalance_next_step,
                )
                # In either case, we disable this rebalance for next time
                self.force_rebalance_next_step = False
                logger.info(f'Est. USD value: {usd_val:.2f}')
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

    def run_backtest(
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
