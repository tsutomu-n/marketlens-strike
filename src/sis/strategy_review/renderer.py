from __future__ import annotations

from sis.strategy_review.manifest import StrategyReviewManifest
from sis.strategy_review.sections import ReviewSection


BOUNDARY_NOTICE = (
    "この review は人間の戦略レビュー用 artifact です。"
    "alpha、paper readiness、live readiness を証明しません。"
)
PACK_VALIDATION_NOTICE = (
    "pack validation PASS でも収益性、paper移行可否、live実行可否は証明しません。"
)


def render_strategy_review_markdown(
    manifest: StrategyReviewManifest,
    sections: list[ReviewSection] | None = None,
) -> str:
    review_sections = sections or []
    strategy_sections = [section for section in review_sections if section.title == "戦略定義"]
    followup_sections = [section for section in review_sections if section.title != "戦略定義"]
    lines: list[str] = [
        f"# Strategy Review: {manifest.review_id}",
        "",
        "## 1. 結論",
        "",
        f"- created_at: `{manifest.created_at}`",
        f"- review_status: `{manifest.review_status.value}`",
        f"- strict: `{str(manifest.strict).lower()}`",
        f"- missing_required_count: `{manifest.summary.missing_required_count}`",
        f"- invalid_required_count: `{manifest.summary.invalid_required_count}`",
        f"- boundary_violation_count: `{manifest.summary.boundary_violation_count}`",
        f"- pack_validation_status: `{manifest.evaluation_flags.pack_validation_status}`",
        "- pack_validation_pass_is_readiness_proof: `false`",
        "",
    ]

    section_number = 2
    for section in strategy_sections:
        lines.extend([f"## {section_number}. {section.title}", "", section.markdown.rstrip(), ""])
        section_number += 1

    lines.extend(
        [
            f"## {section_number}. 入力artifact",
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
    lines.append("")
    section_number += 1

    for section in followup_sections:
        lines.extend([f"## {section_number}. {section.title}", "", section.markdown.rstrip(), ""])
        section_number += 1

    lines.extend(
        [
            f"## {section_number}. Safety Boundary",
            "",
            BOUNDARY_NOTICE,
            "",
            PACK_VALIDATION_NOTICE,
            "",
        ]
    )
    section_number += 1

    problem_rows = [
        artifact
        for artifact in manifest.source_artifacts
        if artifact.status.value != "present" or artifact.summary.get("boundary_violations")
    ]
    lines.extend([f"## {section_number}. Missing / Invalid / Blocked (Needs Attention)", ""])
    if problem_rows:
        for artifact in problem_rows:
            reason = artifact.status.value
            violations = artifact.summary.get("boundary_violations")
            if violations:
                reason = f"boundary_violation: {', '.join(violations)}"
            lines.append(f"- `{artifact.artifact_key}`: {reason} ({artifact.path})")
    else:
        lines.append("- なし。")
    lines.append("")
    section_number += 1

    lines.extend([f"## {section_number}. Human Review Checklist", ""])
    lines.extend(
        [
            "- 必須 artifact が `present` であることを確認する。",
            "- 欠損、invalid、boundary violation があれば先に原因を確認する。",
            "- Strategy Definition と Lifecycle Summary を読み、次に確認する artifact を決める。",
            "- pack validation の結果を戦略評価や readiness proof として読まない。",
            "- source hash table の path と hash を再現性確認に使う。",
            "",
        ]
    )
    return "\n".join(lines)
