from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from sis.strategy_idea_seeds.common.errors import SeedOutputExistsError
from sis.strategy_idea_seeds.common.ids import canonical_hash, sha256_file, stable_id
from sis.strategy_idea_seeds.common.models import (
    DataReadiness,
    SeedArtifactReference,
    SeedInputReference,
    SeedProducer,
    SeedRunManifest,
    StrategyIdeaSeedSet,
)
from sis.strategy_idea_seeds.rendering import render_seed_set_markdown
from sis.strategy_idea_seeds.source.probe import probe_source_root
from sis.strategy_idea_seeds.storage.artifact_writer import (
    write_json_atomic,
    write_jsonl_atomic,
    write_text_atomic,
)
from sis.strategy_idea_seeds.technical.catalog import (
    load_mechanism_pack,
    load_operator_catalog,
)
from sis.strategy_idea_seeds.technical.generator import generate_technical_seeds


PRODUCER_ID = "sis.strategy_idea_seeds.technical"
PRODUCER_VERSION = "1.0.0"


@dataclass(frozen=True)
class TechnicalSeedBuildResult:
    manifest: SeedRunManifest
    seed_set: StrategyIdeaSeedSet
    manifest_path: Path
    source_capabilities_path: Path
    attempts_path: Path
    payloads_path: Path
    seed_set_path: Path
    markdown_path: Path


def build_technical_seeds(
    *,
    source_root: Path,
    mechanism_pack_path: Path,
    operator_catalog_path: Path,
    out_dir: Path,
    created_at: datetime | None = None,
) -> TechnicalSeedBuildResult:
    _prepare_output(out_dir)
    timestamp = (
        (created_at or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    )
    producer = SeedProducer(producer_id=PRODUCER_ID, version=PRODUCER_VERSION)
    source_snapshot = probe_source_root(source_root)
    mechanism_pack = load_mechanism_pack(mechanism_pack_path)
    operator_catalog = load_operator_catalog(operator_catalog_path)
    mechanism_hash = sha256_file(mechanism_pack_path)
    operator_hash = sha256_file(operator_catalog_path)
    config_hash = canonical_hash(
        {"mechanism_pack": mechanism_hash, "operator_catalog": operator_hash}
    )
    attempts, payloads, seeds = generate_technical_seeds(
        mechanism_pack=mechanism_pack,
        operator_catalog=operator_catalog,
        source_snapshot=source_snapshot,
        producer=producer,
        created_at=timestamp,
        config_hash=config_hash,
    )
    semantic_hash = canonical_hash(
        [
            {
                "seed_record_id": seed.seed_record_id,
                "status": seed.status,
                "data_readiness": seed.data_readiness,
                "profit_intent": seed.profit_intent,
                "required_sources": seed.required_sources,
                "known_gaps": seed.known_gaps,
                "falsification_question": seed.falsification_question,
                "payload": seed.payload,
                "provenance_signature": seed.provenance_signature,
                "boundary": seed.boundary,
            }
            for seed in seeds
        ]
    )
    seed_set = StrategyIdeaSeedSet(
        created_at=timestamp,
        producer=producer,
        seed_count=len(seeds),
        data_required_count=sum(
            seed.data_readiness is DataReadiness.DATA_REQUIRED for seed in seeds
        ),
        semantic_hash=semantic_hash,
        seeds=seeds,
    )

    source_capabilities_path = out_dir / "source_capabilities.json"
    attempts_path = out_dir / "technical/technical_attempts.jsonl"
    payloads_path = out_dir / "technical/technical_payloads.jsonl"
    seed_set_path = out_dir / "review/strategy_idea_seed_set.json"
    markdown_path = out_dir / "review/strategy_idea_seed_set.md"
    manifest_path = out_dir / "seed_run_manifest.json"
    write_json_atomic(
        source_capabilities_path,
        source_snapshot.model_dump(mode="json", exclude_none=True),
    )
    write_jsonl_atomic(
        attempts_path,
        (item.model_dump(mode="json", exclude_none=True) for item in attempts),
    )
    write_jsonl_atomic(
        payloads_path,
        (item.model_dump(mode="json", exclude_none=True) for item in payloads),
    )
    write_json_atomic(seed_set_path, seed_set.model_dump(mode="json", exclude_none=True))
    write_text_atomic(markdown_path, render_seed_set_markdown(seed_set))

    reason_counts = Counter(reason.value for attempt in attempts for reason in attempt.reason_codes)
    pruned_indices = [
        attempt.attempt_index
        for attempt in attempts
        if "PRUNED_BUDGET" in {reason.value for reason in attempt.reason_codes}
    ]
    known_gaps = sorted(
        {
            *(
                reason
                for capability in source_snapshot.capabilities
                for reason in capability.reason_codes
            ),
            *(gap for seed in seeds for gap in seed.known_gaps),
        }
    )
    artifacts = [
        _artifact(
            "source_capabilities",
            source_capabilities_path,
            out_dir,
            len(source_snapshot.capabilities),
        ),
        _artifact("technical_attempts", attempts_path, out_dir, len(attempts)),
        _artifact("technical_payloads", payloads_path, out_dir, len(payloads)),
        _artifact("strategy_idea_seed_set", seed_set_path, out_dir, len(seeds)),
        _artifact("strategy_idea_seed_set_markdown", markdown_path, out_dir, len(seeds)),
    ]
    run_id = stable_id(
        "seed-run",
        {
            "source_root_hash": source_snapshot.source_root_hash,
            "config_hash": config_hash,
            "producer_version": PRODUCER_VERSION,
            "git_sha": _git_sha(),
        },
    )
    manifest = SeedRunManifest(
        run_id=run_id,
        created_at=timestamp,
        producer=producer,
        git_sha=_git_sha(),
        inputs=[
            SeedInputReference(
                input_key="source_root",
                path=source_snapshot.source_root,
                sha256=source_snapshot.source_root_hash,
            )
        ],
        configs=[
            SeedInputReference(
                input_key="mechanism_pack",
                path=mechanism_pack_path.resolve().as_posix(),
                sha256=mechanism_hash,
            ),
            SeedInputReference(
                input_key="operator_catalog",
                path=operator_catalog_path.resolve().as_posix(),
                sha256=operator_hash,
            ),
        ],
        attempt_count=len(attempts),
        seed_count=len(seeds),
        data_required_count=seed_set.data_required_count,
        next_cursor=min(pruned_indices) if pruned_indices else None,
        reason_counts=dict(sorted(reason_counts.items())),
        artifacts=artifacts,
        known_gaps=known_gaps,
    )
    write_json_atomic(manifest_path, manifest.model_dump(mode="json", exclude_none=True))
    return TechnicalSeedBuildResult(
        manifest=manifest,
        seed_set=seed_set,
        manifest_path=manifest_path,
        source_capabilities_path=source_capabilities_path,
        attempts_path=attempts_path,
        payloads_path=payloads_path,
        seed_set_path=seed_set_path,
        markdown_path=markdown_path,
    )


def _prepare_output(out_dir: Path) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SeedOutputExistsError(f"output directory is not empty: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)


def _artifact(
    artifact_key: str, path: Path, out_dir: Path, record_count: int
) -> SeedArtifactReference:
    return SeedArtifactReference(
        artifact_key=artifact_key,
        path=path.relative_to(out_dir).as_posix(),
        sha256=sha256_file(path),
        record_count=record_count,
    )


def _git_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()
