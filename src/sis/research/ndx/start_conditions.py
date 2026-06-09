from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from sis.research.dag.review_contracts import Layer22ExitDecision
from sis.research.dag.review_contracts import Layer22FreezeManifest
from sis.research.dag.review_pack import compute_current_pack_hash
from sis.research.ndx.artifacts import DAG_ID, read_json


class Layer23StartConditionError(ValueError):
    """Raised when Layer 2.3 must not start from the current Layer 2.2 state."""


@dataclass(frozen=True)
class Layer23StartConditions:
    dag_id: str
    pack_hash: str
    decision_path: Path
    freeze_manifest_path: Path
    artifact_dir: Path


def require_layer23_start_conditions(
    *,
    root: Path,
    artifact_dir: Path,
) -> Layer23StartConditions:
    review_dir = artifact_dir / "review"
    decision_path = review_dir / "layer_2_2_exit_decision.json"
    freeze_manifest_path = review_dir / "layer_2_2_freeze_manifest.json"
    core_dag_path = artifact_dir / "core_dag.json"
    data_requirements_path = artifact_dir / "data_requirements.yaml"

    for path in (decision_path, freeze_manifest_path, core_dag_path, data_requirements_path):
        if not path.exists():
            raise Layer23StartConditionError(f"required start artifact missing: {path}")

    try:
        decision = Layer22ExitDecision.model_validate(read_json(decision_path))
        freeze_manifest = Layer22FreezeManifest.model_validate(read_json(freeze_manifest_path))
    except (ValidationError, ValueError) as exc:
        raise Layer23StartConditionError(str(exc)) from exc

    if decision.decision != "APPROVE_2_3":
        raise Layer23StartConditionError(
            f"Layer 2.2 decision is not APPROVE_2_3: {decision.decision}"
        )
    if decision.second_review_required:
        raise Layer23StartConditionError("Layer 2.2 approval still requires second review.")
    if decision.unresolved_human_decisions:
        unresolved = ", ".join(decision.unresolved_human_decisions)
        raise Layer23StartConditionError(
            f"Layer 2.2 approval has unresolved human decisions: {unresolved}"
        )
    if decision.dag_id != DAG_ID:
        raise Layer23StartConditionError(f"unexpected dag_id: {decision.dag_id}")
    if freeze_manifest.dag_id != decision.dag_id:
        raise Layer23StartConditionError("freeze manifest dag_id does not match exit decision.")
    if freeze_manifest.pack_hash != decision.pack_hash:
        raise Layer23StartConditionError("freeze manifest pack_hash does not match exit decision.")
    if freeze_manifest.exit_decision != "APPROVE_2_3":
        raise Layer23StartConditionError("freeze manifest does not freeze APPROVE_2_3.")

    current_pack_hash = compute_current_pack_hash(root=root, artifact_dir=artifact_dir)
    if current_pack_hash != decision.pack_hash:
        raise Layer23StartConditionError(
            f"current Layer 2.2 artifact pack_hash mismatch: {current_pack_hash} != {decision.pack_hash}"
        )

    return Layer23StartConditions(
        dag_id=decision.dag_id,
        pack_hash=decision.pack_hash,
        decision_path=decision_path,
        freeze_manifest_path=freeze_manifest_path,
        artifact_dir=artifact_dir,
    )
