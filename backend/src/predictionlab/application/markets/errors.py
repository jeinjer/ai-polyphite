class MarketApplicationError(Exception):
    """Base error for market application use cases."""


class ProviderNotFoundError(MarketApplicationError):
    pass


class ProviderAlreadyExistsError(MarketApplicationError):
    pass


class ProviderDisabledError(MarketApplicationError):
    pass


class MarketNotFoundError(MarketApplicationError):
    pass


class MarketAlreadyExistsError(MarketApplicationError):
    pass


class SnapshotConflictError(MarketApplicationError):
    pass


class ObservationConflictError(MarketApplicationError):
    pass


class ObservationProviderMismatchError(MarketApplicationError):
    pass
