from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def build_historical_archive_preflight_manifest(
    *,
    generated: datetime,
    data_dir: Path,
    aws_status: dict[str, Any],
    command: list[str],
    return_code: int,
    stdout: str,
    stderr: str,
) -> dict[str, Any]:
    return {
        "schema_version": "trade_xyz_historical_archive_preflight_manifest.v1",
        "generated_at": generated.isoformat(),
        "source": "hyperliquid_archive.preflight",
        "data_dir": str(data_dir),
        "aws_available": aws_status["available"],
        "aws_command_source": aws_status["source"],
        "aws_command_prefix": aws_status["command_prefix"],
        "aws_requires_network_for_tool_install": aws_status["requires_network_for_tool_install"],
        "preflight_command": command,
        "return_code": return_code,
        "status": "pass" if return_code == 0 else "fail",
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "notes": [
            "This preflight checks AWS identity before requester-pays archive download.",
            "It does not download historical archive objects.",
        ],
    }
