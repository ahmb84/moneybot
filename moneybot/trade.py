# -*- coding: utf-8 -*-


class AbstractTrade:
    """High-level class representing a trade from one coin to another.
    """

    def __init__(
        self,
        sell_coin: str,
        buy_coin: str,
        reference_coin: str,
        reference_value: float,
    ) -> None:
        self._sell_coin = sell_coin
        self._buy_coin = buy_coin
        self._reference_coin = reference_coin
        self._reference_value = reference_value

    @property
    def sell_coin(self) -> str:
        return self._sell_coin

    @property
    def buy_coin(self) -> str:
        return self._buy_coin

    @property
    def reference_coin(self) -> str:
        return self._reference_coin

    @property
    def reference_value(self) -> float:
        return self._reference_value
