from __future__ import annotations

import json
from pathlib import Path

import typer

from sis.crypto_perp.bitget.probe import ProviderProbeArtifact
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.probe_audit import CryptoPerpProbeAudit
from sis.crypto_perp.raw_refresh import CryptoPerpRawRefreshArtifact, build_raw_refresh


def _render_raw_refresh_markdown(artifact: CryptoPerpRawRefreshArtifact) -> str:
    lines = [
        "# Crypto Perp Raw Refresh",
        "",
        f"- probe_id: `{artifact.probe_id}`",
        f"- probe_audit_status: `{artifact.probe_audit_status}`",
        f"- event_count: `{artifact.event_count}`",
        f"- universe_snapshot_path: `{artifact.universe_snapshot_path}`",
        f"- market_snapshot_path: `{artifact.market_snapshot_path}`",
        f"- quality_report_path: `{artifact.quality_report_path}`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
    ]
    if artifact.event_paths:
        lines.extend(["", "## Events", ""])
        lines.extend(f"- `{path}`" for path in artifact.event_paths)
    if artifact.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in artifact.known_gaps)
    return "\n".join(lines)


def register_crypto_perp_raw_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-raw-refresh")
    def crypto_perp_raw_refresh_cmd(
        probe: Path = typer.Option(
            ...,
            "--probe",
            help="Source crypto_perp_provider_probe.v1 JSON artifact.",
        ),
        probe_audit: Path = typer.Option(
            ...,
            "--probe-audit",
            help="Source crypto_perp_probe_audit.v1 JSON artifact.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/raw_refresh"),
            "--out",
            help="Output directory for raw-derived snapshots and events.",
        ),
    ) -> None:
        try:
            probe_payload = json.loads(probe.read_text(encoding="utf-8"))
            audit_payload = json.loads(probe_audit.read_text(encoding="utf-8"))
            result = build_raw_refresh(
                probe=ProviderProbeArtifact.model_validate(probe_payload),
                audit=CryptoPerpProbeAudit.model_validate(audit_payload),
                out_dir=out,
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        write_json_artifact(out / "universe_snapshot.json", result.universe_payload)
        write_json_artifact(out / "market_snapshot.json", result.market_payload)
        write_json_artifact(out / "candle_quality.json", result.quality_payload)
        for path, payload in zip(result.artifact.event_paths, result.event_payloads, strict=True):
            write_json_artifact(Path(path), payload)
        write_json_artifact(out / "raw_refresh.json", result.artifact.model_dump(mode="json"))
        write_text_artifact(out / "raw_refresh.md", _render_raw_refresh_markdown(result.artifact))
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("status=pass")
        typer.echo(f"event_count={result.artifact.event_count}")
        typer.echo(f"known_gap_count={len(result.artifact.known_gaps)}")
        typer.echo(f"raw_refresh_path={(out / 'raw_refresh.json').as_posix()}")
        typer.echo(f"report_path={(out / 'raw_refresh.md').as_posix()}")
