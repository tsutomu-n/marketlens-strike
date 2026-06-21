from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.bitget.probe import run_provider_probe
from sis.crypto_perp.config import CryptoPerpLabConfig
from sis.crypto_perp.probe_audit import build_probe_audit
from .test_config import valid_config_payload
from .test_provider_probe import _transport


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _probe_and_audit(tmp_path: Path) -> tuple[Path, Path]:
    config = CryptoPerpLabConfig.model_validate(valid_config_payload())
    probe_result = run_provider_probe(
        config=config,
        out_dir=tmp_path / "data/crypto_perp/provider_probe",
        raw_root=tmp_path / "data/crypto_perp/raw",
        transport=_transport(),
        network_attempted=True,
        started_at="2026-06-21T04:30:00Z",
    )
    audit = build_probe_audit(probe=probe_result.probe)
    audit_path = tmp_path / "data/crypto_perp/probe_audit/probe_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit.model_dump(mode="json")), encoding="utf-8")
    return probe_result.probe_path, audit_path


def test_crypto_perp_raw_refresh_cli_builds_snapshots_from_probe_raw(tmp_path: Path) -> None:
    probe_path, audit_path = _probe_and_audit(tmp_path)

    result = runner.invoke(
        app,
        [
            "crypto-perp-raw-refresh",
            "--probe",
            str(probe_path),
            "--probe-audit",
            str(audit_path),
            "--out",
            str(tmp_path / "refresh"),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "event_count=0" in result.stdout

    refresh_path = tmp_path / "refresh/raw_refresh.json"
    payload = json.loads(refresh_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_raw_refresh.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["schema_version"] == "crypto_perp_raw_refresh.v1"
    assert payload["event_count"] == 0
    assert "NO_EVENT_DETECTED" in payload["known_gaps"]
    assert (tmp_path / "refresh/universe_snapshot.json").exists()
    assert (tmp_path / "refresh/market_snapshot.json").exists()
    assert (tmp_path / "refresh/candle_quality.json").exists()


def test_crypto_perp_raw_refresh_cli_requires_ready_audit(tmp_path: Path) -> None:
    probe_path, audit_path = _probe_and_audit(tmp_path)
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    payload["audit_status"] = "BLOCKED_PROBE_QUALITY"
    audit_path.write_text(json.dumps(payload), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "crypto-perp-raw-refresh",
            "--probe",
            str(probe_path),
            "--probe-audit",
            str(audit_path),
            "--out",
            str(tmp_path / "refresh"),
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "READY_FOR_EVENT_REFRESH" in result.stdout
