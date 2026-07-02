from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sis.backtest.artifact_io import sha256_file
from sis.edge_candidate_factory._contracts import (
    CandidateDecision,
    CandidateGateStatus,
    CandidateRowKind,
    CausePrior,
)
from sis.edge_candidate_factory.ledger import (
    EdgeCandidateLedgerWriteResult,
    render_smart_candidate_prior_report_markdown,
    write_edge_candidate_ledgers,
)
from sis.edge_candidate_factory.models import (
    ArtifactRef,
    EdgeCandidateSearchLedgerRow,
    GeneratorConfig,
    ProducerInfo,
    SmartCandidateCard,
    SmartCandidatePriorReport,
    TrialMultiplicityAccount,
)
from sis.edge_candidate_factory.multiplicity import build_trial_multiplicity_account
from sis.edge_candidate_factory.smart_priors import (
    build_default_candidate_card,
    default_smart_prior_family_ids,
    smart_prior_family_by_id,
)
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_review.provenance import normalize_repo_relative_posix_path


ZERO_HASH = "sha256:" + "0" * 64
GENERATOR_VERSION = "edge-candidate-factory-v0"


class EdgeCandidateFactoryError(ValueError):
    pass


class EdgeCandidateFactoryOutputExistsError(EdgeCandidateFactoryError):
    pass


class EdgeCandidateFactoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    source_root: str
    symbols: list[str] = Field(min_length=1)
    product_type: str = "USDT-FUTURES"
    timeframe: str = "5m"
    families: list[str] = Field(default_factory=list)
    candidate_cap: int = Field(ge=1, default=10)
    venue_id: str = "bitget"
    profile: str = "core"
    generated_at: datetime | None = None

    @field_validator("run_id", "product_type", "timeframe", "venue_id", "profile")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("symbols", "families")
    @classmethod
    def validate_text_list(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("list values must not be empty")
        return cleaned

    @field_validator("source_root")
    @classmethod
    def validate_source_root(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @model_validator(mode="after")
    def validate_families(self) -> EdgeCandidateFactoryConfig:
        family_ids = self.families or list(default_smart_prior_family_ids())
        for family_id in family_ids:
            try:
                smart_prior_family_by_id(family_id)
            except KeyError as exc:
                raise ValueError(str(exc)) from exc
        return self


@dataclass(frozen=True)
class EdgeCandidateFactoryRun:
    config: EdgeCandidateFactoryConfig
    report: SmartCandidatePriorReport
    search_ledger_rows: list[EdgeCandidateSearchLedgerRow]
    rejection_rows: list[EdgeCandidateSearchLedgerRow]
    multiplicity_account: TrialMultiplicityAccount


@dataclass(frozen=True)
class EdgeCandidateFactoryWriteResult:
    report_path: Path
    report_markdown_path: Path
    search_ledger_path: Path
    multiplicity_account_path: Path
    rejection_ledger_path: Path
    report_sha256: str
    ledger_result: EdgeCandidateLedgerWriteResult


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def stable_parameter_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _source_root_ref(source_root: str) -> ArtifactRef:
    return ArtifactRef(
        ref_id="source-root",
        schema_version="local_source_root.v1",
        path=source_root,
        sha256=ZERO_HASH,
    )


def _ledger_row_for_card(
    *,
    run_id: str,
    card: SmartCandidateCard,
    row_kind: CandidateRowKind = CandidateRowKind.CANDIDATE,
) -> EdgeCandidateSearchLedgerRow:
    return EdgeCandidateSearchLedgerRow(
        run_id=run_id,
        candidate_id=card.candidate_id,
        row_kind=row_kind,
        family=card.family,
        cause_priors=card.cause_priors,
        parameter_hash=stable_parameter_hash(card.parameter_set),
        parameter_set=card.parameter_set,
        candidate_cluster_id=card.candidate_cluster_id,
        similar_candidate_count=card.similar_candidate_count,
        candidate_prior_score=card.candidate_prior_score,
        candidate_decision=card.candidate_decision,
        rejection_reason=card.rejection_reason,
        source_requirement_status=card.source_requirement_status,
        execution_precheck_status=card.execution_precheck.execution_precheck_status,
        validation_peek_count_at_generation=0,
        sealed_test_used_for_selection=False,
        proof_status="not_alpha_or_profit_proof",
    )


def _rejection_row(
    *,
    config: EdgeCandidateFactoryConfig,
    family_id: str,
    row_kind: CandidateRowKind,
    rejection_reason: str,
    index: int,
) -> EdgeCandidateSearchLedgerRow:
    family = smart_prior_family_by_id(family_id)
    card = build_default_candidate_card(
        family_id,
        candidate_id=f"{config.run_id}-reject-{index:03d}",
        venue_id=config.venue_id,
        product_type=config.product_type,
        symbol=config.symbols[0],
    )
    parameter_set = {
        "family_id": family_id,
        "profile": config.profile,
        "rejection_reason": rejection_reason,
    }
    return EdgeCandidateSearchLedgerRow(
        run_id=config.run_id,
        candidate_id=f"{config.run_id}-{row_kind.value}-{index:03d}",
        row_kind=row_kind,
        family=family_id,
        cause_priors=[CausePrior(cause_prior) for cause_prior in family.cause_priors],
        parameter_hash=stable_parameter_hash(parameter_set),
        parameter_set=parameter_set,
        candidate_cluster_id=family.family_id,
        similar_candidate_count=card.similar_candidate_count,
        candidate_prior_score=card.candidate_prior_score,
        candidate_decision=CandidateDecision.REJECTED,
        rejection_reason=rejection_reason,
        source_requirement_status=CandidateGateStatus.NOT_ESTIMABLE,
        execution_precheck_status=CandidateGateStatus.NOT_ESTIMABLE,
        validation_peek_count_at_generation=0,
        sealed_test_used_for_selection=False,
        proof_status="not_alpha_or_profit_proof",
    )


def _requested_families(config: EdgeCandidateFactoryConfig) -> list[str]:
    return config.families or list(default_smart_prior_family_ids())


def build_edge_candidate_factory_run(config: EdgeCandidateFactoryConfig) -> EdgeCandidateFactoryRun:
    generated_at = config.generated_at or _utc_now()
    requested_families = _requested_families(config)
    seen: set[str] = set()
    candidate_cards: list[SmartCandidateCard] = []
    search_rows: list[EdgeCandidateSearchLedgerRow] = []
    rejection_rows: list[EdgeCandidateSearchLedgerRow] = []
    family_trial_counts: dict[str, int] = {}
    source_refs = [_source_root_ref(config.source_root)]

    for index, family_id in enumerate(requested_families, start=1):
        family_trial_counts[family_id] = family_trial_counts.get(family_id, 0) + 1
        if family_id in seen:
            row = _rejection_row(
                config=config,
                family_id=family_id,
                row_kind=CandidateRowKind.DUPLICATE,
                rejection_reason="duplicate family requested before generation",
                index=index,
            )
            search_rows.append(row)
            rejection_rows.append(row)
            continue
        seen.add(family_id)
        if len(candidate_cards) >= config.candidate_cap:
            row = _rejection_row(
                config=config,
                family_id=family_id,
                row_kind=CandidateRowKind.CAP_REJECTION,
                rejection_reason="candidate cap exceeded before generation",
                index=index,
            )
            search_rows.append(row)
            rejection_rows.append(row)
            continue

        card = build_default_candidate_card(
            family_id,
            candidate_id=f"{config.run_id}-{len(candidate_cards) + 1:03d}",
            venue_id=config.venue_id,
            product_type=config.product_type,
            symbol=config.symbols[0],
        )
        candidate_cards.append(card)
        search_rows.append(_ledger_row_for_card(run_id=config.run_id, card=card))

    report = SmartCandidatePriorReport(
        report_id=config.run_id,
        generated_at=generated_at,
        producer=ProducerInfo(command="edge-candidate-factory-build"),
        source_refs=source_refs,
        generator_config=GeneratorConfig(
            profile=config.profile,
            symbols=config.symbols,
            product_type=config.product_type,
            timeframe=config.timeframe,
            families=list(dict.fromkeys(requested_families)),
            candidate_cap=config.candidate_cap,
            parameter_grid_hash=stable_parameter_hash(
                {"families": requested_families, "candidate_cap": config.candidate_cap}
            ),
            source_root=config.source_root,
            sealed_test_policy="do_not_use_for_selection",
        ),
        candidate_cards=candidate_cards,
        candidate_count_total=len(candidate_cards),
        candidate_count_accepted=len(candidate_cards),
        candidate_count_rejected=0,
        rejection_summary={
            "duplicate": sum(
                1 for row in rejection_rows if row.row_kind is CandidateRowKind.DUPLICATE
            ),
            "cap_rejection": sum(
                1 for row in rejection_rows if row.row_kind is CandidateRowKind.CAP_REJECTION
            ),
        },
        score_summary={
            "max_total_score": max(
                (card.candidate_prior_score.total_score for card in candidate_cards), default=0.0
            ),
            "candidate_cap": float(config.candidate_cap),
        },
        known_gaps=[
            "source availability not checked in T4",
            "selection-adjusted metrics are not estimated",
            "not alpha or profit proof",
        ],
    )
    multiplicity_account = build_trial_multiplicity_account(
        account_id=f"{config.run_id}-multiplicity",
        created_at=generated_at,
        source_refs=source_refs,
        candidate_run_id=config.run_id,
        search_ledger_rows=search_rows,
        expected_trial_count=len(search_rows),
        validation_peek_count=0,
        rerank_count=0,
        known_gaps=[
            "source availability not checked in T4",
        ],
    )
    return EdgeCandidateFactoryRun(
        config=config,
        report=report,
        search_ledger_rows=search_rows,
        rejection_rows=rejection_rows,
        multiplicity_account=multiplicity_account,
    )


def _output_paths(out_dir: Path) -> tuple[Path, Path, Path, Path, Path]:
    return (
        out_dir / "smart_candidate_prior_report.json",
        out_dir / "smart_candidate_prior_report.md",
        out_dir / "edge_candidate_search_ledger.jsonl",
        out_dir / "trial_multiplicity_account.json",
        out_dir / "candidate_rejections.jsonl",
    )


def write_edge_candidate_factory_run(
    *,
    run: EdgeCandidateFactoryRun,
    out_dir: Path,
    replace_existing: bool = False,
) -> EdgeCandidateFactoryWriteResult:
    paths = _output_paths(out_dir)
    if not replace_existing:
        existing = [path for path in paths if path.exists()]
        if existing:
            raise EdgeCandidateFactoryOutputExistsError(
                "output already exists: " + ", ".join(path.as_posix() for path in existing)
            )

    report_path, report_markdown_path, _, multiplicity_path, _ = paths
    write_json_artifact(report_path, run.report.model_dump(mode="json", exclude_none=True))
    write_text_artifact(
        report_markdown_path,
        render_smart_candidate_prior_report_markdown(
            run.report,
            run.multiplicity_account,
            rejection_row_count=len(run.rejection_rows),
        ),
    )
    ledger_result = write_edge_candidate_ledgers(
        out_dir=out_dir,
        search_rows=run.search_ledger_rows,
        rejection_rows=run.rejection_rows,
    )
    write_json_artifact(
        multiplicity_path,
        run.multiplicity_account.model_dump(mode="json", exclude_none=True),
    )
    return EdgeCandidateFactoryWriteResult(
        report_path=report_path,
        report_markdown_path=report_markdown_path,
        search_ledger_path=ledger_result.search_ledger_path,
        multiplicity_account_path=multiplicity_path,
        rejection_ledger_path=ledger_result.rejection_ledger_path,
        report_sha256=sha256_file(report_path),
        ledger_result=ledger_result,
    )
