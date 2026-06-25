from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

import typer

from sis.crypto_perp.bitget.probe import ProviderProbeArtifact, run_provider_probe
from sis.crypto_perp.config import CryptoPerpLabConfig
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.probe_audit import CryptoPerpProbeAudit, build_probe_audit
from sis.crypto_perp.reason_codes import CryptoPerpReasonCode


def _render_probe_audit_markdown(audit: CryptoPerpProbeAudit) -> str:
    lines = [
        "# Crypto Perp Probe Audit",
        "",
        f"- probe_id: `{audit.probe_id}`",
        f"- audit_status: `{audit.audit_status}`",
        f"- raw_snapshot_count: `{audit.raw_snapshot_count}`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
    ]
    if audit.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in audit.known_gaps)
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- `{action}`" for action in audit.next_actions)
    return "\n".join(lines)


def register_crypto_perp_probe_commands(
    app: typer.Typer,
    *,
    load_config_for_cli_fn: Callable[[Path], tuple[CryptoPerpLabConfig, Path]],
    env_enabled_fn: Callable[[str], bool],
    utc_now_fn: Callable[[], datetime],
) -> None:
    @app.command("crypto-perp-probe")
    def crypto_perp_probe_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/provider_probe"),
            "--out",
            help="Output directory for provider probe artifacts.",
        ),
        raw_root: Path = typer.Option(
            Path("data/crypto_perp/raw"),
            "--raw-root",
            help="Root directory for immutable raw public snapshots.",
        ),
        network: bool = typer.Option(
            False,
            "--network/--no-network",
            help="Attempt public network only when env opt-in is also set.",
        ),
    ) -> None:
        lab_config, _resolved = load_config_for_cli_fn(config)
        env_name = lab_config.network_policy.public_network_env_var
        typer.echo(f"config_id={lab_config.config_id}")
        if not network or not env_enabled_fn(env_name):
            typer.echo("network_attempted=false")
            typer.echo("status=blocked")
            typer.echo(f"block_reason={CryptoPerpReasonCode.PUBLIC_NETWORK_OPT_IN_REQUIRED.value}")
            raise typer.Exit(2)
        try:
            result = run_provider_probe(
                config=lab_config,
                out_dir=out,
                raw_root=raw_root,
                network_attempted=True,
                started_at=utc_now_fn(),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("network_attempted=true")
        typer.echo("credentials_used=false")
        typer.echo("status=pass")
        typer.echo(f"probe_id={result.probe.probe_id}")
        typer.echo(f"probe_path={result.probe_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")

    @app.command("crypto-perp-probe-audit")
    def crypto_perp_probe_audit_cmd(
        probe: Path = typer.Option(
            ...,
            "--probe",
            help="Source crypto_perp_provider_probe.v1 JSON artifact.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/probe_audit"),
            "--out",
            help="Output directory for probe audit artifacts.",
        ),
        check_raw_exists: bool = typer.Option(
            True,
            "--check-raw-exists/--no-check-raw-exists",
            help="Verify raw snapshot paths referenced by the probe exist locally.",
        ),
    ) -> None:
        try:
            payload = json.loads(probe.read_text(encoding="utf-8"))
            probe_artifact = ProviderProbeArtifact.model_validate(payload)
            audit = build_probe_audit(
                probe=probe_artifact,
                check_raw_exists=check_raw_exists,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        json_path = out / "probe_audit.json"
        report_path = out / "probe_audit.md"
        write_json_artifact(json_path, audit.model_dump(mode="json"))
        write_text_artifact(report_path, _render_probe_audit_markdown(audit))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo(
            "status=pass" if audit.audit_status == "READY_FOR_EVENT_REFRESH" else "status=blocked"
        )
        typer.echo(f"audit_status={audit.audit_status}")
        typer.echo(f"known_gap_count={len(audit.known_gaps)}")
        typer.echo(f"probe_audit_path={json_path.as_posix()}")
        typer.echo(f"report_path={report_path.as_posix()}")
