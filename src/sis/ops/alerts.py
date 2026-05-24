from __future__ import annotations

from pathlib import Path


def render_alert_message(
    *,
    level: str,
    title: str,
    body: str,
    source: str,
) -> str:
    return "\n".join(
        [
            f"[{level.upper()}] {title}",
            f"source: {source}",
            body,
        ]
    )


def write_alert(path: Path, *, level: str, title: str, body: str, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_alert_message(level=level, title=title, body=body, source=source) + "\n",
        encoding="utf-8",
    )
    return path
