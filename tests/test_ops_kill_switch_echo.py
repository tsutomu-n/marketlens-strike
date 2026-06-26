from sis.commands.ops_kill_switch_echo import kill_switch_status_lines


def test_kill_switch_status_lines_preserve_cli_order() -> None:
    assert kill_switch_status_lines(
        {
            "enabled": True,
            "path": "data/state/kill_switch.flag",
        }
    ) == [
        "enabled=True",
        "path=data/state/kill_switch.flag",
    ]


def test_kill_switch_status_lines_match_missing_value_echo_behavior() -> None:
    assert kill_switch_status_lines({}) == [
        "enabled=None",
        "path=None",
    ]
