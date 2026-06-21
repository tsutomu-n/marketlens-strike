from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.config import CryptoPerpLabConfig, load_crypto_perp_lab_config
from sis.crypto_perp.models import CryptoPerpBoundary
from support.cli import normalized_stdout


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/crypto_perp_lab_config.v1.schema.json").read_text(encoding="utf-8")
    )


def valid_config_payload() -> dict:
    return {
        "schema_version": "crypto_perp_lab_config.v1",
        "config_id": "bitget-personal-edge-lab",
        "created_at": "2026-06-21T04:00:00Z",
        "provider": {
            "provider_id": "bitget",
            "product_type": "USDT-FUTURES",
            "base_url": "https://api.bitget.com",
        },
        "network_policy": {
            "default_external_network_allowed": False,
            "public_network_env_var": "SIS_ALLOW_PUBLIC_NETWORK",
            "credentialed_read_env_var": "SIS_ALLOW_CREDENTIALED_READ",
            "tiny_live_env_var": "SIS_ENABLE_TINY_LIVE_MEASUREMENT",
        },
        "heartbeat": {
            "instruments_interval_seconds": 300,
            "tickers_interval_seconds": 30,
            "open_interest_interval_seconds": 60,
        },
        "universe": {
            "quote_asset": "USDT",
            "require_online_status": True,
            "min_listing_age_hours": 24,
        },
        "screening": {
            "history_backfill_hours": 336,
            "candle_interval": "15m",
            "slow_window_hours": 74,
            "slow_return_threshold": "0.04",
            "slow_turnover_impulse_threshold": "0.15",
            "fast_window_minutes": 60,
            "fast_abs_return_floor": "0.03",
            "fast_robust_z_threshold": "3.0",
            "fast_turnover_percentile_threshold": "0.95",
        },
        "candidate_capture": {
            "max_concurrent_captures": 5,
            "duration_minutes": 360,
            "channels": ["trades", "books1", "books15"],
            "channel_limit_per_connection": 50,
        },
        "outcomes": {"horizon_minutes": [5, 15, 60, 240, 720, 1440]},
        "execution_replay": {
            "notional_grid_usd": ["5", "10", "25", "50", "100", "250"],
            "latency_grid_seconds": [5, 15, 30, 60],
        },
        "capital": {
            "capital_ceiling_usd": "3000",
            "lifetime_experiment_budget_usd": "300",
            "measurement_notional_min_usd": "5",
            "measurement_notional_max_usd": "25",
            "allow_top_up": False,
            "max_open_positions": 1,
        },
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
        },
    }


def test_crypto_perp_lab_config_schema_accepts_valid_payload() -> None:
    payload = valid_config_payload()

    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    CryptoPerpLabConfig.model_validate(payload)


def test_crypto_perp_lab_config_pydantic_dump_matches_schema() -> None:
    config = CryptoPerpLabConfig.model_validate(valid_config_payload())
    dumped = config.model_dump(mode="json")

    Draft202012Validator(_schema()).validate(dumped)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update({"unexpected": "nope"}),
        lambda payload: payload["created_at"].replace("Z", ""),
        lambda payload: payload["heartbeat"].update({"tickers_interval_seconds": -1}),
        lambda payload: payload["screening"].update({"history_backfill_hours": 100}),
        lambda payload: payload["network_policy"].update(
            {"default_external_network_allowed": True}
        ),
        lambda payload: payload["boundary"].update({"exchange_write_used": True}),
        lambda payload: payload["capital"].update({"capital_ceiling_usd": "3000.01"}),
        lambda payload: payload["capital"].update({"measurement_notional_max_usd": "25.01"}),
        lambda payload: payload["capital"].update({"allow_top_up": True}),
        lambda payload: payload["capital"].update({"max_open_positions": 2}),
    ],
)
def test_crypto_perp_lab_config_rejects_unsafe_shape(mutate) -> None:
    payload = valid_config_payload()
    result = mutate(payload)
    if isinstance(result, str):
        payload["created_at"] = result

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        CryptoPerpLabConfig.model_validate(payload)


def test_crypto_perp_boundary_defaults_are_false() -> None:
    boundary = CryptoPerpBoundary()

    assert boundary.model_dump() == {
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def test_load_crypto_perp_lab_config_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "crypto_perp.yaml"
    config_path.write_text(
        yaml.safe_dump(valid_config_payload(), sort_keys=False), encoding="utf-8"
    )

    config = load_crypto_perp_lab_config(config_path)

    assert config.config_id == "bitget-personal-edge-lab"
    assert config.network_policy.default_external_network_allowed is False


def test_crypto_perp_config_validate_help() -> None:
    result = runner.invoke(app, ["crypto-perp-config-validate", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--config" in stdout
    assert "crypto_perp_lab_config.v1" in stdout


def test_crypto_perp_config_validate_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "configs/crypto_perp/config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(valid_config_payload(), sort_keys=False), encoding="utf-8"
    )

    result = runner.invoke(
        app,
        [
            "crypto-perp-config-validate",
            "--config",
            str(config_path),
            "--out",
            str(tmp_path / "data/crypto_perp/config_validation"),
        ],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "config_id=bitget-personal-edge-lab" in result.stdout
    assert (tmp_path / "data/crypto_perp/config_validation/config_validation.json").exists()
