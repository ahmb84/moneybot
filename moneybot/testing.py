# -*- coding: utf-8 -*-
import json
from datetime import datetime
from typing import Dict
from typing import List

import pandas as pd


class MarketHistoryMock:

    _history = None  # type: Dict
    _charts = None   # type: Dict

    def __init__(self):
        cls = type(self)
        if cls._history is None:
            with open('tests/mock-data/history.json', 'r') as f:
                cls._history = json.load(f)
        if cls._charts is None:
            with open('tests/mock-data/charts.json', 'r') as f:
                cls._charts = json.load(f)

    def latest(self, time: datetime) -> Dict[str, Dict[str, float]]:
        return type(self)._charts[f'{time!s}']

    def asset_history(
        self,
        time: str,
        base: str,
        quote: str,
        days_back=30,
        key='price_usd',
    ) -> List[float]:
        parsed_dict = type(self)._history[f'{time!s}-{base}-{quote}']
        # HACK marshalling HACK
        # 1. reset index of parsed dict
        # 2. transpose from a row to a column
        # 3. reverse that column
        df = pd.DataFrame(parsed_dict, index=[0]).transpose().iloc[::-1]
        return df
