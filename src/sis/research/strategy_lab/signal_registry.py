from __future__ import annotations

from collections.abc import Callable
from typing import Any

import polars as pl

SignalGenerator = Callable[[pl.DataFrame, Any], pl.DataFrame]


class SignalGeneratorRegistry:
    def __init__(self) -> None:
        self._generators: dict[str, SignalGenerator] = {}

    def register(self, generator_id: str, generator: SignalGenerator) -> None:
        normalized = generator_id.strip()
        if not normalized:
            raise ValueError("generator_id must be non-empty")
        if normalized in self._generators:
            raise ValueError(f"Signal generator already registered: {normalized}")
        self._generators[normalized] = generator

    def get(self, generator_id: str) -> SignalGenerator:
        normalized = generator_id.strip()
        try:
            return self._generators[normalized]
        except KeyError as exc:
            raise KeyError(f"Unknown signal generator: {normalized}") from exc

    def run(self, generator_id: str, frame: pl.DataFrame, spec: Any) -> pl.DataFrame:
        return self.get(generator_id)(frame, spec)

    def registered_ids(self) -> list[str]:
        return sorted(self._generators)
