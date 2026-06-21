from __future__ import annotations

import json
from pathlib import Path

import httpx
from jsonschema import Draft202012Validator
from typer.testing import CliRunner
import yaml

from sis.cli import app
from sis.crypto_perp.bitget.probe import run_provider_probe
from sis.crypto_perp.config import CryptoPerpLabConfig
from support.cli import normalized_stdout
from .test_config import valid_config_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures/crypto_perp/bitget/public"
runner = CliRunner()


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _transport() -> httpx.MockTransport:
    responses = {
        "/api/v3/market/instruments": _fixture("instruments.json"),
        "/api/v3/market/tickers": _fixture("tickers.json"),
        "/api/v3/market/candles": _fixture("candles.json"),
        "/api/v3/market/open-interest": _fixture("open_interest.json"),
        "/api/v3/market/history-fund-rate": _fixture("funding_history.json"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=responses[request.url.path])

    return httpx.MockTransport(handler)


def test_provider_probe_builds_artifact_and_raw_snapshots(tmp_path: Path) -> None:
    config = CryptoPerpLabConfig.model_validate(valid_config_payload())

    result = run_provider_probe(
        config=config,
        out_dir=tmp_path / "data/crypto_perp/provider_probe",
        raw_root=tmp_path / "data/crypto_perp/raw",
        transport=_transport(),
        network_attempted=True,
        started_at="2026-06-21T04:30:00Z",
    )

    payload = result.probe.model_dump(mode="json")
    endpoint_ids = {item["endpoint_id"] for item in payload["endpoint_results"]}
    assert endpoint_ids == {
        "instruments",
        "tickers",
        "candles",
        "open_interest",
        "funding_history",
    }
    assert payload["credentials_used"] is False
    assert payload["network_attempted"] is True
    assert payload["capabilities"]["instruments"] is True
    assert any("candle_limit" in item for item in payload["documentation_anomalies"])
    assert result.probe_path.exists()
    assert result.report_path.exists()
    assert len(list((tmp_path / "data/crypto_perp/raw").rglob("*.json"))) == 5


def test_provider_probe_dump_matches_schema(tmp_path: Path) -> None:
    config = CryptoPerpLabConfig.model_validate(valid_config_payload())
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_provider_probe.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    result = run_provider_probe(
        config=config,
        out_dir=tmp_path / "data/crypto_perp/provider_probe",
        raw_root=tmp_path / "data/crypto_perp/raw",
        transport=_transport(),
        network_attempted=True,
        started_at="2026-06-21T04:30:00Z",
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.probe.model_dump(mode="json"))


def test_crypto_perp_probe_cli_requires_network_opt_in(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SIS_ALLOW_PUBLIC_NETWORK", raising=False)
    config_path = tmp_path / "configs/crypto_perp/config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(valid_config_payload(), sort_keys=False), encoding="utf-8"
    )

    result = runner.invoke(
        app,
        [
            "crypto-perp-probe",
            "--config",
            str(config_path),
            "--out",
            str(tmp_path / "probe"),
            "--raw-root",
            str(tmp_path / "raw"),
            "--network",
        ],
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 2
    assert "network_attempted=false" in stdout
    assert "block_reason=public_network_opt_in_required" in stdout
    assert not (tmp_path / "raw").exists()
