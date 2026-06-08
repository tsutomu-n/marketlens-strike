from __future__ import annotations

import json
from pathlib import Path

from sis.research.dag.review_contracts import Layer22ExitDecision
from sis.research.dag.review_contracts import Layer22FreezeManifest
from sis.research.dag.review_pack import _artifact_hashes


def build_freeze_manifest(
    *,
    root: Path,
    artifact_dir: Path,
    decision: Layer22ExitDecision,
) -> Layer22FreezeManifest:
    artifact_hashes = _artifact_hashes(root=root, artifact_dir=artifact_dir)
    return Layer22FreezeManifest(
        schema_version="layer_2_2_freeze_manifest.v1",
        dag_id=decision.dag_id,
        pack_hash=decision.pack_hash,
        exit_decision="APPROVE_2_3",
        review_ids=decision.review_ids,
        artifact_hashes=artifact_hashes,
        frozen_artifacts=sorted(artifact_hashes),
        created_at=decision.created_at,
    )


def write_freeze_manifest(
    *,
    root: Path,
    artifact_dir: Path,
    decision: Layer22ExitDecision,
    out_path: Path,
) -> Path:
    manifest = build_freeze_manifest(root=root, artifact_dir=artifact_dir, decision=decision)
    out_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_path
