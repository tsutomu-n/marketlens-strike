from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewSection:
    title: str
    markdown: str
