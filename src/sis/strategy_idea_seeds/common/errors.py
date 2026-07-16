from __future__ import annotations


class StrategyIdeaSeedError(ValueError):
    """Base error for Seed Foundry contract failures."""


class SeedInputError(StrategyIdeaSeedError):
    """Raised when a source or config input cannot be interpreted."""


class SeedOutputExistsError(StrategyIdeaSeedError):
    """Raised when a run would overwrite an existing output."""
