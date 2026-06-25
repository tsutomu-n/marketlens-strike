from __future__ import annotations

from pathlib import Path

from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.promotion_decision import PromotionDecision


def _write_paper_preview_candidate_pack(*, data_dir: Path, pack: PaperCandidatePack) -> Path:
    out = data_dir / "research/paper_candidate_pack.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    return out


def _write_paper_preview_promotion_decision(*, data_dir: Path, decision: PromotionDecision) -> Path:
    out = data_dir / "research/promotion_decision.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(decision.model_dump_json(indent=2), encoding="utf-8")
    return out


def _write_paper_preview_json_outputs(
    *, data_dir: Path, pack: PaperCandidatePack, decision: PromotionDecision
) -> dict[str, Path]:
    return {
        "paper_candidate_pack": _write_paper_preview_candidate_pack(data_dir=data_dir, pack=pack),
        "promotion_decision": _write_paper_preview_promotion_decision(
            data_dir=data_dir,
            decision=decision,
        ),
    }
