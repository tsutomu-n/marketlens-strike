from __future__ import annotations

from pathlib import Path

from sis.storage.jsonl_store import write_json
from sis.venues.trade_xyz.models import TradeXyzRegistryBuildResult


def build_trade_xyz_universe_report(build_result: TradeXyzRegistryBuildResult) -> str:
    resolved = [row for row in build_result.resolutions if row.asset_id is not None]
    unresolved = [row for row in build_result.resolutions if row.asset_id is None]
    active = [row for row in build_result.instruments if row.active]
    paper_only = [row for row in build_result.instruments if row.active and not row.api_orderable]
    excluded = [row for row in build_result.resolutions if row.excluded]
    unresolved_fields = [
        row for row in build_result.resolutions if row.index_in_meta is None or row.asset_id is None
    ]

    lines = [
        "# Trade[XYZ] Universe Report",
        "",
        f"- resolved instruments: {len(resolved)}",
        f"- unresolved instruments: {len(unresolved)}",
        f"- active tracking universe: {len(active)}",
        f"- paper-only universe: {len(paper_only)}",
        "",
        "## Resolved Instruments",
    ]
    if resolved:
        lines.extend(
            [
                f"- {row.symbol}: asset_id={row.asset_id} (perp_dex_index={row.perp_dex_index}, index_in_meta={row.index_in_meta})"
                for row in resolved
            ]
        )
    else:
        lines.append("- none")

    lines.extend(["", "## Unresolved Instruments"])
    if unresolved:
        lines.extend([f"- {row.symbol}: asset_id unresolved" for row in unresolved])
    else:
        lines.append("- none")

    lines.extend(["", "## Active Tracking Universe"])
    lines.extend([f"- {item.canonical_symbol}" for item in active] or ["- none"])

    lines.extend(["", "## Paper-only Universe"])
    lines.extend([f"- {item.canonical_symbol}" for item in paper_only] or ["- none"])

    lines.extend(["", "## Excluded Symbols"])
    lines.extend([f"- {row.symbol}" for row in excluded] or ["- none"])

    lines.extend(["", "## Unresolved API Fields"])
    if unresolved_fields:
        lines.extend(
            [
                f"- {row.symbol}: perp_dex_index={row.perp_dex_index}, index_in_meta={row.index_in_meta}, asset_id={row.asset_id}, has_mid={row.has_mid_price}"
                for row in unresolved_fields
            ]
        )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Next Blocking Questions",
            "- confirm perp_dex_index from live Trade[XYZ] meta/perpDexs payload",
            "- confirm missing symbols in meta/allMids before enabling api_orderable",
            "- keep excluded symbols out of active universe until policy changes",
            "",
        ]
    )
    return "\n".join(lines)


def write_trade_xyz_universe_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_trade_xyz_universe_summary(path: Path, build_result: TradeXyzRegistryBuildResult) -> None:
    payload = {
        "resolved_count": len(
            [row for row in build_result.resolutions if row.asset_id is not None]
        ),
        "unresolved_count": len([row for row in build_result.resolutions if row.asset_id is None]),
        "active_count": len([row for row in build_result.instruments if row.active]),
        "paper_only_count": len(
            [row for row in build_result.instruments if row.active and not row.api_orderable]
        ),
        "excluded_symbols": [row.symbol for row in build_result.resolutions if row.excluded],
    }
    write_json(path, payload)
