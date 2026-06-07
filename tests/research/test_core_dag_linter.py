from __future__ import annotations

from sis.research.dag.contracts import CoreDag
from sis.research.dag.linter import lint_core_dag
from sis.research.hypothesis.data_source_contracts import DataSourceRegistry
from sis.research.hypothesis.temporal_contracts import TemporalAvailability
from research.helpers import core_dag_payload


def test_core_dag_linter_rejects_outcome_to_treatment_and_configured_forbidden_edge() -> None:
    payload = core_dag_payload()
    payload["edges"] = [{"from": "outcome", "to": "treatment"}]
    payload["forbidden_edges"] = [{"from": "outcome", "to": "treatment", "reason": "bad"}]
    dag = CoreDag.model_validate(payload)

    issues = lint_core_dag(dag)

    assert {issue.rule_id for issue in issues if issue.severity == "error"} == {
        "outcome_to_treatment",
        "configured_forbidden_edge",
    }


def test_core_dag_linter_rejects_future_to_signal_edge_and_warns_missing_counter_dag() -> None:
    dag = CoreDag.model_validate(
        {
            "schema_version": "core_dag.v1",
            "dag_id": "T",
            "name": "future",
            "scope_id": "S",
            "nodes": [
                {"id": "outcome", "role": "outcome"},
                {"id": "signal", "role": "treatment_candidate"},
            ],
            "edges": [{"from": "outcome", "to": "signal"}],
        }
    )
    temporal = TemporalAvailability.model_validate(
        {
            "schema_version": "research_temporal_availability.v1",
            "layers": {
                "t_after_close": ["outcome"],
                "t_open_plus_buffer": ["signal"],
            },
        }
    )

    issues = lint_core_dag(dag, temporal=temporal)

    assert "future_to_signal" in {issue.rule_id for issue in issues}
    assert "missing_counter_dag" in {issue.rule_id for issue in issues}


def test_core_dag_linter_warns_when_optional_provider_source_is_required() -> None:
    dag = CoreDag.model_validate(
        {
            "schema_version": "core_dag.v1",
            "dag_id": "T",
            "name": "optional_required",
            "scope_id": "S",
            "nodes": [
                {"id": "nq_overnight_move_optional", "role": "observed_proxy"},
                {"id": "signal", "role": "treatment_candidate"},
            ],
            "edges": [{"from": "nq_overnight_move_optional", "to": "signal"}],
            "data_requirements": [
                {
                    "variable_id": "nq_overnight_move_optional",
                    "source_symbol": "NQ",
                    "formula": "optional futures proxy",
                    "temporal_class": "provider_dependent",
                    "provider_candidates": ["future_provider"],
                    "requirement_tier": "required",
                }
            ],
        }
    )
    data_sources = DataSourceRegistry.model_validate(
        {
            "schema_version": "research_data_sources.v1",
            "sources": {
                "NQ": {
                    "description": "futures price discovery proxy",
                    "source_tier": "optional_provider_dependent",
                    "default_proxy_for": ["nq_overnight_move_optional"],
                }
            },
        }
    )

    issues = lint_core_dag(dag, data_sources=data_sources)

    assert "optional_provider_required" in {issue.rule_id for issue in issues}
