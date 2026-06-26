from sis.commands.ops_alert_echo import alert_output_text


def test_alert_output_text_preserves_multiline_text() -> None:
    rendered_text = "[WARN] Stale\nsource: codex\nrecollect"

    assert alert_output_text(rendered_text) == rendered_text


def test_alert_output_text_preserves_trailing_newline() -> None:
    rendered_text = "[INFO] Ready\nsource: codex\ncontinue\n"

    assert alert_output_text(rendered_text) == rendered_text
