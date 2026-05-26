from sis.reports.implementation_status import implementation_status_markdown


def test_implementation_status_markdown_includes_current_live_evidence_steps() -> None:
    text = implementation_status_markdown()

    assert "PR-08" in text
    assert "trade_xyz" in text
    assert "micro_live_safety_report" in text
    assert "public CLI からの micro live 実行 surface" in text
