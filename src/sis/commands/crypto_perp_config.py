from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import typer
from pydantic import ValidationError

from sis.crypto_perp.config import CryptoPerpLabConfig
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import ConfigValidationArtifact, CryptoPerpProducer, stable_hash


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _config_hash(config_path: Path) -> str:
    return "sha256:" + stable_hash([config_path.read_text(encoding="utf-8")])


def _write_config_validation(
    config_path: Path,
    out_dir: Path,
    *,
    load_config_for_cli_fn: Callable[[Path], tuple[CryptoPerpLabConfig, Path]],
) -> ConfigValidationArtifact:
    config, resolved = load_config_for_cli_fn(config_path)
    artifact = ConfigValidationArtifact(
        artifact_id=stable_hash(
            ["crypto-perp-config-validate", config.config_id, _config_hash(resolved)]
        ),
        created_at=_utc_now(),
        producer=CryptoPerpProducer(command="crypto-perp-config-validate"),
        config_id=config.config_id,
        config_hash=_config_hash(resolved),
    )
    payload = artifact.model_dump(mode="json")
    write_json_artifact(out_dir / "config_validation.json", payload)
    write_text_artifact(
        out_dir / "config_validation.md",
        "\n".join(
            [
                "# Crypto Perp Config Validation",
                "",
                f"- config_id: `{artifact.config_id}`",
                f"- validation_status: `{artifact.validation_status}`",
                "- boundary: all normal flags false",
            ]
        ),
    )
    return artifact


def register_crypto_perp_config_commands(
    app: typer.Typer,
    *,
    load_config_for_cli_fn: Callable[[Path], tuple[CryptoPerpLabConfig, Path]],
) -> None:
    @app.command("crypto-perp-config-validate")
    def crypto_perp_config_validate_cmd(
        config: Path = typer.Option(
            ...,
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/config_validation"),
            "--out",
            help="Output directory for config validation artifacts.",
        ),
    ) -> None:
        try:
            artifact = _write_config_validation(
                config,
                out,
                load_config_for_cli_fn=load_config_for_cli_fn,
            )
        except (ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"config_id={artifact.config_id}")
        typer.echo(f"validation_status={artifact.validation_status}")
        typer.echo(f"validation_path={(out / 'config_validation.json').as_posix()}")
        typer.echo(f"report_path={(out / 'config_validation.md').as_posix()}")
