from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sis.storage.jsonl_store import append_jsonl, write_json


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


def queue_notification(
    *,
    outbox_path: Path,
    latest_path: Path,
    level: str,
    title: str,
    body: str,
    source: str,
    sink: str = "local_outbox",
    now: datetime | None = None,
) -> dict[str, object]:
    current = now.astimezone(timezone.utc) if now and now.tzinfo else (now or datetime.now(timezone.utc))
    record: dict[str, object] = {
        "notification_id": current.strftime("%Y%m%d_%H%M%S_%f"),
        "created_at": current.isoformat(),
        "status": "queued",
        "sink": sink,
        "level": level,
        "title": title,
        "body": body,
        "source": source,
        "rendered_text": render_alert_message(level=level, title=title, body=body, source=source),
    }
    append_jsonl(outbox_path, record)
    write_json(latest_path, record)
    return record
