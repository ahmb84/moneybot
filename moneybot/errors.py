# -*- coding: utf-8 -*-


class OrderValidationError(Exception):
    pass


class InsufficientBalanceError(OrderValidationError):
    pass


class OrderTooSmallError(OrderValidationError):
    pass


class NoMarketAvailableError(Exception):
    pass
