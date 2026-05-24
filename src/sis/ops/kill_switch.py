from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class KillSwitch:
    def __init__(self, path: Path) -> None:
        self.path = path

    def enable(self, reason: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = f"enabled_at={datetime.now(timezone.utc).isoformat()}\nreason={reason}\n"
        self.path.write_text(payload, encoding="utf-8")

    def disable(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def is_enabled(self) -> bool:
        return self.path.exists()

    def status(self) -> dict:
        return {
            "enabled": self.is_enabled(),
            "path": str(self.path),
            "details": self.path.read_text(encoding="utf-8") if self.path.exists() else None,
        }
