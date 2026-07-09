from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

import typer

from sis.commands.crypto_perp_account import (
    register_crypto_perp_account_commands,
)
from sis.commands.crypto_perp_backtest_candidate_pack import (
    register_crypto_perp_backtest_candidate_pack_commands,
)
from sis.commands.crypto_perp_candidate_leaderboard import (
    register_crypto_perp_candidate_leaderboard_commands,
)
from sis.commands.crypto_perp_config import register_crypto_perp_config_commands
from sis.commands.crypto_perp_no_cash_backtest_gate import (
    register_crypto_perp_no_cash_backtest_gate_commands,
)
from sis.commands.crypto_perp_no_trade_kill_report import (
    register_crypto_perp_no_trade_kill_report_commands,
)
from sis.commands.crypto_perp_no_cash_backtest_sample import (
    register_crypto_perp_no_cash_backtest_sample_commands,
)
from sis.commands.crypto_perp_order_preview import register_crypto_perp_order_preview_commands
from sis.commands.crypto_perp_probe import register_crypto_perp_probe_commands
from sis.commands.crypto_perp_profit_readiness import (
    register_crypto_perp_profit_readiness_commands,
)
from sis.commands.crypto_perp_real_market_no_cash_sample import (
    register_crypto_perp_real_market_no_cash_sample_commands,
)
from sis.commands.crypto_perp_real_market_ticker_coverage_status import (
    register_crypto_perp_real_market_ticker_coverage_status_commands,
)
from sis.commands.crypto_perp_records import register_crypto_perp_record_commands
from sis.commands.crypto_perp_risk_taker_review import (
    register_crypto_perp_risk_taker_review_commands,
)
from sis.commands.crypto_perp_status import register_crypto_perp_status_commands
from sis.commands.crypto_perp_tournament_report import (
    register_crypto_perp_tournament_report_commands,
)
from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.crypto_perp.config import load_crypto_perp_lab_config
from sis.settings import get_settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _load_config_for_cli(config_path: Path):
    settings = get_settings()
    resolved = _resolve_workspace_path(config_path, settings.data_dir)
    return load_crypto_perp_lab_config(resolved), resolved


def _env_enabled(name: str) -> bool:
    return os.getenv(name) == "1"


def register_crypto_perp_commands(app: typer.Typer) -> None:
    register_crypto_perp_record_commands(app)
    register_crypto_perp_tournament_report_commands(app)
    register_crypto_perp_profit_readiness_commands(app)
    register_crypto_perp_backtest_candidate_pack_commands(app)
    register_crypto_perp_no_trade_kill_report_commands(app)
    register_crypto_perp_candidate_leaderboard_commands(app)
    register_crypto_perp_no_cash_backtest_gate_commands(app)
    register_crypto_perp_no_cash_backtest_sample_commands(app)
    register_crypto_perp_real_market_no_cash_sample_commands(app)
    register_crypto_perp_real_market_ticker_coverage_status_commands(app)
    register_crypto_perp_risk_taker_review_commands(app)
    register_crypto_perp_config_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
    )
    register_crypto_perp_probe_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
        env_enabled_fn=_env_enabled,
        utc_now_fn=_utc_now,
    )
    register_crypto_perp_account_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
        env_enabled_fn=_env_enabled,
        utc_now_fn=_utc_now,
    )
    register_crypto_perp_order_preview_commands(app, utc_now_fn=_utc_now)
    register_crypto_perp_status_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
    )
