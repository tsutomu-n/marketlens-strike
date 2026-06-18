from __future__ import annotations

from sis.strategy_review.manifest import SourceArtifact, StrategyReviewManifest
from sis.strategy_review.sections import ReviewSection


BOUNDARY_NOTICE = (
    "このreviewは人間の戦略レビュー用artifactです。\n"
    "alpha、paper readiness、live readinessを証明しません。"
)
PACK_VALIDATION_NOTICE = (
    "backtest pack validation が PASS の場合でも、"
    "戦略の収益性、paper移行可否、live実行可否は証明されません。"
)
LIFECYCLE_NOTICE = (
    "Lifecycle decision は paper / live 実行許可ではありません。"
    "人間が次に確認する状態整理として読みます。"
)


def _section_by_id(sections: list[ReviewSection], section_id: str) -> ReviewSection | None:
    return next((section for section in sections if section.section_id == section_id), None)


def _empty_section(section_id: str, title: str, status: str, markdown: str) -> ReviewSection:
    return ReviewSection(section_id=section_id, title=title, status=status, markdown=markdown)


def _artifact_error(artifact: SourceArtifact) -> str:
    if artifact.error:
        return artifact.error
    violations = artifact.summary.get("boundary_violations")
    if isinstance(violations, list) and violations:
        return ", ".join(str(item) for item in violations)
    return ""


def render_strategy_review_markdown(
    manifest: StrategyReviewManifest,
    sections: list[ReviewSection] | None = None,
) -> str:
    review_sections = sections or []
    backtest_section = _section_by_id(
        review_sections, "backtest_pack_validation_summary"
    ) or _empty_section(
        "backtest_pack_validation_summary",
        "Backtest Pack / Validation Summary",
        "missing",
        "- status: `missing`",
    )
    strategy_section = _section_by_id(review_sections, "strategy_definition") or _empty_section(
        "strategy_definition",
        "Strategy Definition",
        "not_configured",
        "- status: `not_configured`",
    )
    lifecycle_section = _section_by_id(review_sections, "lifecycle_summary") or _empty_section(
        "lifecycle_summary",
        "Lifecycle Summary",
        "missing",
        "- status: `missing`",
    )
    optional_context_sections = [
        section
        for section in (
            _section_by_id(review_sections, "input_contract_summary"),
            _section_by_id(review_sections, "idea_intake_summary"),
        )
        if section is not None
    ]

    lines: list[str] = [
        f"# Strategy Review: {manifest.review_id}",
        "",
        "## 1. Summary",
        "",
        f"- created_at: `{manifest.created_at}`",
        f"- producer.tool: `{manifest.producer.tool}`",
        f"- producer.command: `{manifest.producer.command}`",
        f"- producer.schema_version: `{manifest.producer.schema_version}`",
        f"- review_status: `{manifest.review_status.value}`",
        f"- source_safety.status: `{manifest.source_safety.status.value}`",
        f"- strict: `{str(manifest.strict).lower()}`",
        f"- missing_required_count: `{manifest.summary.missing_required_count}`",
        f"- invalid_required_count: `{manifest.summary.invalid_required_count}`",
        f"- boundary_violation_count: `{manifest.summary.boundary_violation_count}`",
        f"- unknown_boundary_count: `{manifest.summary.unknown_boundary_count}`",
        f"- pack_validation_status: `{manifest.evaluation_flags.pack_validation_status}`",
        "- pack_validation_pass_is_readiness_proof: `false`",
        "",
        "## 2. Readiness Disclaimer",
        "",
        BOUNDARY_NOTICE,
        "",
        PACK_VALIDATION_NOTICE,
        "",
        "## 3. Source Artifact Status",
        "",
        "| artifact | required | status | path | error |",
        "|---|---:|---|---|---|",
    ]

    for artifact in manifest.source_artifacts:
        lines.append(
            "| "
            f"`{artifact.artifact_key}` | "
            f"{str(artifact.required).lower()} | "
            f"`{artifact.status.value}` | "
            f"`{artifact.path}` | "
            f"`{_artifact_error(artifact)}` |"
        )

    lines.extend(
        [
            "",
            f"## 4. {backtest_section.title}",
            "",
            backtest_section.markdown.rstrip(),
            "",
            f"## 5. {strategy_section.title}",
            "",
            strategy_section.markdown.rstrip(),
            "",
        ]
    )

    next_section_number = 6
    for section in optional_context_sections:
        lines.extend(
            [
                f"## {next_section_number}. {section.title}",
                "",
                section.markdown.rstrip(),
                "",
            ]
        )
        next_section_number += 1

    lines.extend(
        [
            f"## {next_section_number}. {lifecycle_section.title}",
            "",
            LIFECYCLE_NOTICE,
            "",
            lifecycle_section.markdown.rstrip(),
            "",
            f"## {next_section_number + 1}. Safety Boundary",
            "",
            f"- builder_safety.permits_live_order: `{str(manifest.builder_safety.permits_live_order).lower()}`",
            f"- builder_safety.live_conversion_allowed: `{str(manifest.builder_safety.live_conversion_allowed).lower()}`",
            f"- builder_safety.wallet_used: `{str(manifest.builder_safety.wallet_used).lower()}`",
            f"- builder_safety.signing_used: `{str(manifest.builder_safety.signing_used).lower()}`",
            f"- builder_safety.exchange_write_used: `{str(manifest.builder_safety.exchange_write_used).lower()}`",
            f"- source_safety.status: `{manifest.source_safety.status.value}`",
            f"- source_safety.boundary_violation_count: `{manifest.source_safety.boundary_violation_count}`",
            f"- source_safety.unknown_boundary_count: `{manifest.source_safety.unknown_boundary_count}`",
            f"- source_safety.observed_flags: `{manifest.source_safety.observed_flags.model_dump(mode='json')}`",
            "",
            BOUNDARY_NOTICE,
            "",
            PACK_VALIDATION_NOTICE,
            "",
        ]
    )

    problem_rows = [
        artifact
        for artifact in manifest.source_artifacts
        if artifact.status.value != "present" or artifact.summary.get("boundary_violations")
    ]
    lines.extend([f"## {next_section_number + 2}. Missing / Invalid / Blocked Details", ""])
    if problem_rows:
        for artifact in problem_rows:
            reason = artifact.status.value
            error = _artifact_error(artifact)
            if error:
                reason = f"{reason}: {error}"
            lines.append(f"- `{artifact.artifact_key}`: {reason} (`{artifact.path}`)")
    else:
        lines.append("- なし。")
    lines.extend(
        [
            "",
            f"## {next_section_number + 3}. Source Hash Table",
            "",
            "| path | status | bytes | sha256 | detected_schema_version |",
            "|---|---|---:|---|---|",
        ]
    )
    for artifact in manifest.source_artifacts:
        lines.append(
            "| "
            f"`{artifact.path}` | "
            f"`{artifact.status.value}` | "
            f"`{artifact.bytes if artifact.bytes is not None else ''}` | "
            f"`{artifact.sha256 or ''}` | "
            f"`{artifact.detected_schema_version or ''}` |"
        )
    lines.extend(
        [
            "",
            f"## {next_section_number + 4}. Next Human Review Checklist",
            "",
            "- Summary の `review_status`、`source_safety.status`、`strict` を先に確認する。",
            "- 必須 artifact が `present` であることを Source Artifact Status で確認する。",
            "- 欠損、invalid、blocked があれば Missing / Invalid / Blocked Details の原因を先に解消する。",
            "- Strategy Definition と Lifecycle Summary を読み、戦略内容と lifecycle decision を分けて判断する。",
            "- pack validation の結果を戦略評価や readiness proof として読まない。",
            "- Source Hash Table の path、bytes、hash、schema version を再現性確認に使う。",
            "- paper observation 候補にする場合も、この review から直接 paper flow を呼ばず、strategy-review-record で operator_review.yaml に判断を保存してから別の paper revalidation を通す。",
            "",
        ]
    )
    return "\n".join(lines)
