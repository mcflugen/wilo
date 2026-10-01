from __future__ import annotations


class WiloError(Exception):
    pass


class WiloValidationError(WiloError):
    pass


class WiloIOError(WiloError):
    pass


class WiloOptimizationError(WiloError):
    pass
