from __future__ import annotations

from sis.strategy_review.manifest import StrategyReviewManifest


BOUNDARY_NOTICE = (
    "この review は人間の戦略レビュー用 artifact です。"
    "alpha、paper readiness、live readiness を証明しません。"
)
PACK_VALIDATION_NOTICE = (
    "pack validation PASS でも収益性、paper移行可否、live実行可否は証明しません。"
)


def render_strategy_review_markdown(manifest: StrategyReviewManifest) -> str:
    lines: list[str] = [
        f"# Strategy Review: {manifest.review_id}",
        "",
        f"- created_at: `{manifest.created_at}`",
        f"- review_status: `{manifest.review_status.value}`",
        f"- strict: `{str(manifest.strict).lower()}`",
        "",
        "## Boundary",
        "",
        BOUNDARY_NOTICE,
        "",
        PACK_VALIDATION_NOTICE,
        "",
        "## Status Summary",
        "",
        f"- missing_required_count: `{manifest.summary.missing_required_count}`",
        f"- invalid_required_count: `{manifest.summary.invalid_required_count}`",
        f"- boundary_violation_count: `{manifest.summary.boundary_violation_count}`",
        f"- pack_validation_status: `{manifest.evaluation_flags.pack_validation_status}`",
        "- pack_validation_pass_is_readiness_proof: `false`",
        "",
    ]

    problem_rows = [
        artifact
        for artifact in manifest.source_artifacts
        if artifact.status.value != "present" or artifact.summary.get("boundary_violations")
    ]
    if problem_rows:
        lines.extend(["## Needs Attention", ""])
        for artifact in problem_rows:
            reason = artifact.status.value
            violations = artifact.summary.get("boundary_violations")
            if violations:
                reason = f"boundary_violation: {', '.join(violations)}"
            lines.append(f"- `{artifact.artifact_key}`: {reason} ({artifact.path})")
        lines.append("")

    lines.extend(
        [
            "## Source Artifacts",
            "",
            "| artifact | required | status | path | sha256 |",
            "|---|---:|---|---|---|",
        ]
    )
    for artifact in manifest.source_artifacts:
        lines.append(
            "| "
            f"`{artifact.artifact_key}` | "
            f"{str(artifact.required).lower()} | "
            f"`{artifact.status.value}` | "
            f"`{artifact.path}` | "
            f"`{artifact.sha256 or ''}` |"
        )

    lines.extend(["", "## Human Review Checklist", ""])
    lines.extend(
        [
            "- 必須 artifact が `present` であることを確認する。",
            "- 欠損、invalid、boundary violation があれば先に原因を確認する。",
            "- pack validation の結果を戦略評価や readiness proof として読まない。",
            "- source hash table の path と hash を再現性確認に使う。",
            "",
        ]
    )
    return "\n".join(lines)
