"""Typed replay failures safe to persist and expose by type."""

from predictionlab.providers.base import ProviderProtocolError


class ReplayDatasetError(ProviderProtocolError):
    """Base error for an unusable historical dataset."""


class ReplayDatasetFormatError(ReplayDatasetError):
    """The JSONL structure or declared metadata is invalid."""


class ReplayDatasetIntegrityError(ReplayDatasetError):
    """The dataset content does not match its declared SHA-256."""


class ReplayLookaheadError(ReplayDatasetError):
    """A caller attempted to reveal data beyond simulated time."""


class ReplayModeError(ValueError):
    """A replay mode received an incompatible argument."""
