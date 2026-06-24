from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from typing import Any, Callable, cast

from sis.storage.jsonl_store import read_json

HYPERLIQUID_ARCHIVE_BUCKET = "s3://hyperliquid-archive"


@dataclass(frozen=True)
class HistoricalL2ArchiveRequest:
    coin: str
    date: date
    hour: int
    data_type: str = "l2Book"

    def __post_init__(self) -> None:
        if not self.coin:
            raise ValueError("coin is required")
        if self.hour < 0 or self.hour > 23:
            raise ValueError("hour must be between 0 and 23")
        if self.data_type != "l2Book":
            raise ValueError("only l2Book historical archive collection is supported")

    @property
    def date_part(self) -> str:
        return self.date.strftime("%Y%m%d")

    @property
    def s3_uri(self) -> str:
        return (
            f"{HYPERLIQUID_ARCHIVE_BUCKET}/market_data/"
            f"{self.date_part}/{self.hour}/{self.data_type}/{self.coin}.lz4"
        )

    @property
    def output_relative_path(self) -> Path:
        return (
            Path("raw/historical_archive/hyperliquid/market_data")
            / self.date_part
            / str(self.hour)
            / self.data_type
            / self.coin
        )


CommandRunner = Callable[[list[str]], None]
PreflightRunner = Callable[[list[str]], tuple[int, str, str]]


def run_command(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with exit {completed.returncode}: {' '.join(command)}")


def aws_download_command_status() -> dict[str, Any]:
    configured = os.environ.get("SIS_AWS_COMMAND")
    if configured:
        prefix = shlex.split(configured)
        return {
            "available": bool(prefix),
            "source": "SIS_AWS_COMMAND",
            "path": prefix[0] if prefix else None,
            "command_prefix": prefix,
            "requires_network_for_tool_install": False,
        }
    aws_path = shutil.which("aws")
    if aws_path is not None:
        return {
            "available": True,
            "source": "system_aws",
            "path": aws_path,
            "command_prefix": [aws_path],
            "requires_network_for_tool_install": False,
        }
    uv_path = shutil.which("uv")
    if uv_path is not None:
        return {
            "available": True,
            "source": "uv_awscli_fallback",
            "path": uv_path,
            "command_prefix": [uv_path, "run", "--with", "awscli", "aws"],
            "requires_network_for_tool_install": True,
        }
    return {
        "available": False,
        "source": "missing",
        "path": None,
        "command_prefix": ["aws"],
        "requires_network_for_tool_install": False,
    }


def download_command(s3_uri: str, destination: Path) -> list[str]:
    return [
        *aws_download_command_status()["command_prefix"],
        "s3",
        "cp",
        s3_uri,
        str(destination),
        "--request-payer",
        "requester",
    ]


def historical_archive_preflight_status(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "manifests/trade_xyz_historical_archive_preflight_manifest.json"
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "status": None,
            "return_code": None,
            "aws_command_source": None,
        }
    payload = read_json(path)
    if not isinstance(payload, dict):
        return {
            "path": str(path),
            "exists": True,
            "status": "invalid",
            "return_code": None,
            "aws_command_source": None,
        }
    payload = cast(dict[str, Any], payload)
    return {
        "path": str(path),
        "exists": True,
        "status": payload.get("status"),
        "return_code": payload.get("return_code"),
        "aws_command_source": payload.get("aws_command_source"),
    }


def historical_archive_preflight_error(status: dict[str, Any]) -> str | None:
    if status.get("status") == "pass":
        return None
    if not status.get("exists"):
        return (
            "historical archive AWS preflight has not been run; run "
            "`uv run sis check-trade-xyz-historical-archive-preflight` before --execute"
        )
    return (
        "historical archive AWS preflight has not passed; configure AWS credentials or "
        'SIS_AWS_COMMAND="aws --profile <profile>", then rerun '
        "`uv run sis check-trade-xyz-historical-archive-preflight`"
    )


def decompress_lz4(
    source: Path,
    destination: Path,
    *,
    command_runner: CommandRunner = run_command,
) -> None:
    lz4 = shutil.which("lz4")
    if lz4 is None:
        raise RuntimeError(
            "lz4 executable not found; install lz4 before decompressing archive data"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    command_runner([lz4, "-d", "-f", str(source), str(destination)])
