from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewSection:
    section_id: str
    title: str
    status: str
    markdown: str
    source_artifact_keys: tuple[str, ...] = ()
