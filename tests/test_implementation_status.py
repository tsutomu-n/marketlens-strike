from sis.reports.implementation_status import implementation_status_markdown


def test_implementation_status_markdown_includes_current_live_evidence_steps() -> None:
    text = implementation_status_markdown()

    assert "stale_rate" in text
    assert "tradable_rate" in text
    assert "log-quotes --venue gtrade --replace" in text
    assert "cost matrix integration" in text
