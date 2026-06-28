from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_idea_candidates.generator import (
    PERP_REQUIRED_PARAMETER_FIELDS,
    StrategyIdeaCandidateProfile,
    stable_parameter_grid_hash,
)
from sis.strategy_idea_candidates.ledger import (
    parameter_set_hash,
    write_strategy_idea_candidate_search_ledger,
)
from sis.strategy_idea_candidates.models import (
    CandidateDecision,
    SearchLedgerSummary,
    SelectionAdjustedMetricsStatus,
    SelectionPolicy,
    StrategyIdeaCandidate,
    StrategyIdeaCandidateSet,
)
from sis.strategy_idea_candidates.rendering import render_strategy_idea_candidate_set_markdown
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_review.provenance import repo_relative_path


AI_PACKET_SCHEMA_VERSION = "strategy_idea_candidates_ai_packet.v1"
AI_IMPORT_GENERATOR_VERSION = "manual-ai-candidate-import-v1"


@dataclass(frozen=True)
class StrategyIdeaCandidateAIPacketResult:
    packet: dict[str, Any]
    packet_path: Path
    report_path: Path


@dataclass(frozen=True)
class StrategyIdeaCandidateAIImportResult:
    candidate_set: StrategyIdeaCandidateSet
    candidate_set_path: Path
    report_path: Path
    ledger_path: Path


class StrategyIdeaCandidateAIError(ValueError):
    pass


class StrategyIdeaCandidateAIOutputExistsError(StrategyIdeaCandidateAIError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash_payload(payload: object) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _read_json_object_with_message(path: Path) -> dict[str, Any]:
    try:
        return read_json_object(path)
    except json.JSONDecodeError as exc:
        raise StrategyIdeaCandidateAIError(f"invalid JSON: {path}: {exc}") from exc


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise StrategyIdeaCandidateAIError(f"failed to read ledger: {path}: {exc}") from exc
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StrategyIdeaCandidateAIError(
                f"invalid ledger JSONL at line {line_no}: {exc}"
            ) from exc
        if not isinstance(row, dict):
            raise StrategyIdeaCandidateAIError(f"ledger line {line_no} must be an object")
        rows.append(row)
    return rows


def _candidate_summary(candidate: StrategyIdeaCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.idea_candidate_id,
        "family": candidate.family,
        "decision": candidate.decision.value,
        "side_bias": candidate.parameter_set.get("side_bias"),
        "product_type": candidate.parameter_set.get("product_type"),
        "parameter_set_hash": parameter_set_hash(candidate.parameter_set),
        "selection_adjusted_metrics_status": (candidate.selection_adjusted_metrics_status.value),
    }


def build_ai_candidate_packet(
    *,
    candidate_set_path: Path,
    ledger_path: Path,
    out_dir: Path,
    packet_id: str = "strategy-idea-candidates-ai-packet",
    replace_existing: bool = False,
    generated_at: datetime | None = None,
) -> StrategyIdeaCandidateAIPacketResult:
    packet_path = out_dir / "ai_candidate_packet.json"
    report_path = out_dir / "ai_candidate_packet.md"
    if not replace_existing and (packet_path.exists() or report_path.exists()):
        raise StrategyIdeaCandidateAIOutputExistsError(f"output already exists: {out_dir}")

    candidate_set = StrategyIdeaCandidateSet.model_validate(read_json_object(candidate_set_path))
    ledger_rows = _read_jsonl(ledger_path)
    summary = candidate_set.search_ledger_summary
    created = generated_at or _utc_now()
    base_packet: dict[str, Any] = {
        "schema_version": AI_PACKET_SCHEMA_VERSION,
        "packet_id": packet_id,
        "generated_at": _serialize_datetime(created),
        "producer": {"tool": "sis", "command": "strategy-idea-candidates-ai-packet-build"},
        "candidate_set_ref": {
            "path": repo_relative_path(candidate_set_path),
            "sha256": sha256_file(candidate_set_path),
            "candidate_set_id": candidate_set.candidate_set_id,
        },
        "ledger_ref": {
            "path": repo_relative_path(ledger_path),
            "sha256": sha256_file(ledger_path),
            "row_count": len(ledger_rows),
        },
        "profile": StrategyIdeaCandidateProfile.CRYPTO_PERP_RISK_TAKER.value,
        "product_constraints": {
            "venue": "bitget",
            "product_type": "USDT-FUTURES",
            "margin_mode": "isolated",
            "margin_coin": "USDT",
            "max_leverage": 3,
            "required_cost_fields": [
                "funding_assumption",
                "fee_model_ref",
                "slippage_model_ref",
                "liquidation_buffer_bps",
            ],
        },
        "safety_constraints": {
            "live_actions_allowed": False,
            "credentialed_actions_allowed": False,
            "public_network_required": False,
            "write_actions_allowed": False,
        },
        "search_ledger_summary": {
            "candidate_count_total": summary.candidate_count_total,
            "candidate_count_shortlisted": summary.candidate_count_shortlisted,
            "candidate_count_rejected": summary.candidate_count_rejected,
            "trial_count_total": summary.trial_count_total,
            "candidate_cap": summary.candidate_cap,
            "selection_adjusted_metrics_status": "NOT_IMPLEMENTED",
            "uses_sealed_test_for_selection": False,
        },
        "known_gaps": list(
            dict.fromkeys(
                [
                    *candidate_set.selection_policy.known_gaps,
                    "AI variations remain UNVERIFIED_CANDIDATE until human review.",
                    "Raw or estimated metrics are not alpha proof or profit proof.",
                ]
            )
        ),
        "candidate_summaries": [
            _candidate_summary(candidate) for candidate in candidate_set.candidate_inventory
        ],
        "requested_response_shape": {
            "prompt_hash": "<copy ai_input_hash exactly>",
            "candidates": [
                {
                    "candidate_id": "id",
                    "family": "perp_momentum_continuation",
                    "title": "short title",
                    "hypothesis_template": "unverified hypothesis",
                    "signal_expression": "local expression",
                    "side_bias": "long|short|both|no_trade",
                    "parameter_set": {
                        "venue": "bitget",
                        "product_type": "USDT-FUTURES",
                        "margin_mode": "isolated",
                        "margin_coin": "USDT",
                        "leverage": 1,
                        "funding_assumption": "modeled",
                        "fee_model_ref": "ref",
                        "slippage_model_ref": "ref",
                        "liquidation_buffer_bps": 2500,
                    },
                    "feature_columns_used": ["mark_price"],
                }
            ],
        },
    }
    ai_input_hash = _hash_payload(base_packet)
    packet = {**base_packet, "ai_input_hash": ai_input_hash}
    write_json_artifact(packet_path, packet)
    write_text_artifact(report_path, _render_ai_packet_markdown(packet))
    return StrategyIdeaCandidateAIPacketResult(
        packet=packet,
        packet_path=packet_path,
        report_path=report_path,
    )


def import_ai_candidate_response(
    *,
    packet_path: Path,
    response_path: Path,
    out_dir: Path,
    replace_existing: bool = False,
    imported_at: datetime | None = None,
) -> StrategyIdeaCandidateAIImportResult:
    packet = _read_json_object_with_message(packet_path)
    if packet.get("schema_version") != AI_PACKET_SCHEMA_VERSION:
        raise StrategyIdeaCandidateAIError(
            "packet schema_version must be strategy_idea_candidates_ai_packet.v1"
        )
    response = _read_json_object_with_message(response_path)
    prompt_hash = response.get("prompt_hash")
    if not isinstance(prompt_hash, str) or not prompt_hash.strip():
        raise StrategyIdeaCandidateAIError("response prompt_hash is required")
    if prompt_hash != packet.get("ai_input_hash"):
        raise StrategyIdeaCandidateAIError("response prompt_hash must match packet ai_input_hash")
    raw_candidates = response.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise StrategyIdeaCandidateAIError("response candidates must be a non-empty array")

    source_candidate_set_path = _resolve_packet_ref_path(packet["candidate_set_ref"]["path"])
    source_candidate_set = StrategyIdeaCandidateSet.model_validate(
        read_json_object(source_candidate_set_path)
    )
    existing_ids = {
        candidate.idea_candidate_id for candidate in source_candidate_set.candidate_inventory
    }
    imported_candidates = [
        _candidate_from_ai_response(
            raw_candidate=raw_candidate,
            source_candidate_set=source_candidate_set,
            prompt_hash=prompt_hash,
            input_hash=packet["ai_input_hash"],
            trial_index=source_candidate_set.search_ledger_summary.trial_count_total + index,
            existing_ids=existing_ids,
        )
        for index, raw_candidate in enumerate(raw_candidates, start=1)
    ]

    timestamp = imported_at or _utc_now()
    parameter_grids = {
        **source_candidate_set.parameter_grids,
        "ai_generated": [candidate.parameter_set for candidate in imported_candidates],
    }
    parameter_grid_hash = stable_parameter_grid_hash(parameter_grids)
    candidate_inventory = [*source_candidate_set.candidate_inventory, *imported_candidates]
    shortlisted_ids = [
        candidate.idea_candidate_id
        for candidate in candidate_inventory
        if candidate.decision is CandidateDecision.SHORTLISTED
    ]
    rejected_ids = [
        candidate.idea_candidate_id
        for candidate in candidate_inventory
        if candidate.decision is CandidateDecision.REJECTED
    ]
    imported_set = source_candidate_set.model_copy(
        update={
            "candidate_set_id": f"{source_candidate_set.candidate_set_id}-ai-import",
            "generated_at": timestamp,
            "generator_version": AI_IMPORT_GENERATOR_VERSION,
            "candidate_inventory": candidate_inventory,
            "parameter_grids": parameter_grids,
            "search_ledger_summary": SearchLedgerSummary(
                family_count=len(parameter_grids),
                candidate_count_total=len(candidate_inventory),
                candidate_count_shortlisted=len(shortlisted_ids),
                candidate_count_rejected=len(rejected_ids),
                trial_count_total=(
                    source_candidate_set.search_ledger_summary.trial_count_total
                    + len(imported_candidates)
                ),
                parameter_grid_hash=parameter_grid_hash,
                candidate_cap=source_candidate_set.search_ledger_summary.candidate_cap,
                cap_rejection_count=source_candidate_set.search_ledger_summary.cap_rejection_count,
                validation_peek_count=source_candidate_set.search_ledger_summary.validation_peek_count,
                rerank_count=source_candidate_set.search_ledger_summary.rerank_count,
                duplicate_rejection_count=(
                    source_candidate_set.search_ledger_summary.duplicate_rejection_count
                ),
            ),
            "selection_policy": SelectionPolicy(
                policy_id="manual-ai-import-v1",
                description=(
                    "Imported AI-generated variations as rejected, unverified candidates "
                    "requiring human shortlist."
                ),
                shortlisted_candidate_ids=shortlisted_ids,
                rejected_candidate_ids=rejected_ids,
                known_gaps=list(
                    dict.fromkeys(
                        [
                            *source_candidate_set.selection_policy.known_gaps,
                            "AI-generated candidates require human review before shortlist.",
                        ]
                    )
                ),
            ),
        },
    )
    imported_set = StrategyIdeaCandidateSet.model_validate(
        imported_set.model_dump(mode="json", exclude_none=True)
    )
    candidate_set_path = out_dir / "strategy_idea_candidate_set.json"
    report_path = out_dir / "strategy_idea_candidate_set.md"
    if not replace_existing and (candidate_set_path.exists() or report_path.exists()):
        raise StrategyIdeaCandidateAIOutputExistsError(f"output already exists: {out_dir}")
    write_json_artifact(candidate_set_path, imported_set.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_strategy_idea_candidate_set_markdown(imported_set))
    prompt_hash_by_candidate_id = {
        candidate.idea_candidate_id: prompt_hash for candidate in imported_candidates
    }
    ledger = write_strategy_idea_candidate_search_ledger(
        candidate_set=imported_set,
        out_dir=out_dir,
        source_kind="deterministic_generator",
        prompt_hash_by_candidate_id=prompt_hash_by_candidate_id,
        replace_existing=replace_existing,
    )
    _rewrite_ai_import_ledger_sources(
        ledger.ledger_path,
        ai_candidate_ids=set(prompt_hash_by_candidate_id),
    )
    return StrategyIdeaCandidateAIImportResult(
        candidate_set=imported_set,
        candidate_set_path=candidate_set_path,
        report_path=report_path,
        ledger_path=ledger.ledger_path,
    )


def _render_ai_packet_markdown(packet: dict[str, Any]) -> str:
    lines = [
        f"# Strategy Idea Candidates AI Packet: {packet['packet_id']}",
        "",
        f"- ai_input_hash: `{packet['ai_input_hash']}`",
        f"- candidate_set_id: `{packet['candidate_set_ref']['candidate_set_id']}`",
        f"- candidate_count_total: `{packet['search_ledger_summary']['candidate_count_total']}`",
        f"- product_type: `{packet['product_constraints']['product_type']}`",
        f"- max_leverage: `{packet['product_constraints']['max_leverage']}`",
        "- live_actions_allowed: `false`",
        "- credentialed_actions_allowed: `false`",
        "- write_actions_allowed: `false`",
        "",
        "## Request",
        "",
        "Generate additional unverified Bitget USDT-FUTURES hypothesis variations. Return JSON only, copy the ai_input_hash into prompt_hash, and include funding, fee, slippage, leverage, and liquidation-buffer assumptions for every candidate.",
        "",
        "## Known Gaps",
        "",
    ]
    lines.extend(f"- {gap}" for gap in packet["known_gaps"])
    lines.extend(["", "## Candidate Summaries", ""])
    for candidate in packet["candidate_summaries"]:
        lines.append(
            "- "
            f"`{candidate['candidate_id']}` "
            f"{candidate['family']} "
            f"{candidate['decision']} "
            f"{candidate['parameter_set_hash']}"
        )
    return "\n".join(lines) + "\n"


def _resolve_packet_ref_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else Path.cwd() / path


def _candidate_from_ai_response(
    *,
    raw_candidate: Any,
    source_candidate_set: StrategyIdeaCandidateSet,
    prompt_hash: str,
    input_hash: str,
    trial_index: int,
    existing_ids: set[str],
) -> StrategyIdeaCandidate:
    if not isinstance(raw_candidate, dict):
        raise StrategyIdeaCandidateAIError("AI candidate entries must be objects")
    _reject_live_permission_claims(raw_candidate)
    candidate_id = raw_candidate.get("candidate_id") or raw_candidate.get("idea_candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise StrategyIdeaCandidateAIError("AI candidate candidate_id is required")
    if candidate_id in existing_ids:
        raise StrategyIdeaCandidateAIError(f"duplicate AI candidate id: {candidate_id}")
    parameter_set = raw_candidate.get("parameter_set")
    if not isinstance(parameter_set, dict):
        raise StrategyIdeaCandidateAIError(f"{candidate_id}: parameter_set is required")
    _validate_ai_perp_parameter_set(candidate_id, parameter_set)
    template = source_candidate_set.candidate_inventory[0]
    try:
        return StrategyIdeaCandidate(
            idea_candidate_id=candidate_id,
            decision=CandidateDecision.REJECTED,
            family=_required_text(raw_candidate, "family"),
            title=_required_text(raw_candidate, "title"),
            hypothesis_template=_required_text(raw_candidate, "hypothesis_template"),
            mechanism_status="UNVERIFIED_AI_GENERATED",
            signal_expression=_required_text(raw_candidate, "signal_expression"),
            parameter_set={
                **parameter_set,
                "side_bias": raw_candidate.get("side_bias") or parameter_set.get("side_bias"),
            },
            parameter_grid_ref=f"ai:{input_hash}",
            target_definition=template.target_definition,
            prediction_horizon=template.prediction_horizon,
            timeframe=template.timeframe,
            instruments=template.instruments,
            label_window=template.label_window,
            feature_observation_window=template.feature_observation_window,
            feature_columns_used=_feature_columns_from_ai(
                raw_candidate, template.feature_columns_used
            ),
            available_at_policy=template.available_at_policy,
            source_artifact_sha256=template.source_artifact_sha256,
            trial_count_refs=[f"ai-trial-{trial_index:03d}"],
            baseline_refs=template.baseline_refs,
            novelty_checks={
                "source_kind": "ai_generated",
                "prompt_hash": prompt_hash,
                "duplicate_signal": False,
            },
            raw_validation_metrics={
                "source_kind": "ai_generated",
                "prompt_hash": prompt_hash,
                "input_hash": input_hash,
                "metric_basis": "ai_generated_unverified_not_profit_proof",
            },
            selection_adjusted_metrics_status=SelectionAdjustedMetricsStatus.NOT_IMPLEMENTED,
            leakage_checks={
                "uses_sealed_test_for_selection": False,
                "available_at_policy_recorded": True,
                "ai_generated": True,
            },
            rejection_reason="AI-generated candidate requires human shortlist and validation",
        )
    except ValidationError as exc:
        raise StrategyIdeaCandidateAIError(f"invalid AI candidate {candidate_id}: {exc}") from exc


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise StrategyIdeaCandidateAIError(f"AI candidate {key} is required")
    return value.strip()


def _feature_columns_from_ai(payload: dict[str, Any], fallback: list[str]) -> list[str]:
    value = payload.get("feature_columns_used")
    if isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value):
        return [item.strip() for item in value]
    return fallback


def _validate_ai_perp_parameter_set(candidate_id: str, parameter_set: dict[str, Any]) -> None:
    missing = [
        field
        for field in PERP_REQUIRED_PARAMETER_FIELDS
        if parameter_set.get(field) in (None, "", [])
    ]
    if missing:
        raise StrategyIdeaCandidateAIError(f"{candidate_id}: missing {', '.join(missing)}")
    if parameter_set.get("venue") != "bitget":
        raise StrategyIdeaCandidateAIError(f"{candidate_id}: venue must be bitget")
    if parameter_set.get("product_type") != "USDT-FUTURES":
        raise StrategyIdeaCandidateAIError(f"{candidate_id}: product_type must be USDT-FUTURES")
    if parameter_set.get("margin_mode") != "isolated":
        raise StrategyIdeaCandidateAIError(f"{candidate_id}: margin_mode must be isolated")
    if parameter_set.get("margin_coin") != "USDT":
        raise StrategyIdeaCandidateAIError(f"{candidate_id}: margin_coin must be USDT")
    leverage = parameter_set.get("leverage")
    if not isinstance(leverage, int | float) or leverage <= 0 or leverage > 3:
        raise StrategyIdeaCandidateAIError(f"{candidate_id}: leverage must be between 1 and 3")
    liquidation_buffer = parameter_set.get("liquidation_buffer_bps")
    if not isinstance(liquidation_buffer, int | float) or liquidation_buffer <= 0:
        raise StrategyIdeaCandidateAIError(
            f"{candidate_id}: liquidation_buffer_bps must be positive"
        )


def _reject_live_permission_claims(payload: Any) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            if (
                lowered
                in {
                    "permits_live_order",
                    "live_order_submitted",
                    "live_allowed",
                    "wallet_used",
                    "signing_used",
                    "exchange_write_used",
                }
                and value is not False
            ):
                raise StrategyIdeaCandidateAIError("AI response contains live permission claim")
            _reject_live_permission_claims(value)
    elif isinstance(payload, list):
        for item in payload:
            _reject_live_permission_claims(item)


def _rewrite_ai_import_ledger_sources(ledger_path: Path, *, ai_candidate_ids: set[str]) -> None:
    rows = _read_jsonl(ledger_path)
    for row in rows:
        if row.get("candidate_id") in ai_candidate_ids:
            row["source_kind"] = "ai_generated"
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if rows:
        text += "\n"
    write_text_artifact(ledger_path, text)
