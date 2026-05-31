from pathlib import Path
import subprocess


SHELL_WRAPPERS = [
    "scripts/check_trade_xyz_data_prereqs.sh",
    "scripts/collect_trade_xyz_data_cycle.sh",
    "scripts/collect_trade_xyz_data_until_ready.sh",
]


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_trade_xyz_shell_wrappers_are_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", *SHELL_WRAPPERS],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_trade_xyz_prereq_wrapper_enforces_archive_and_account_fee_flags() -> None:
    text = _read("scripts/check_trade_xyz_data_prereqs.sh")

    assert "SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT:-1" in text
    assert "SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE:-1" in text
    assert "check-trade-xyz-historical-archive-preflight" in text
    assert 'SIS_AWS_COMMAND="aws --profile <profile>"' in text
    assert "export SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=0x..." in text
    assert "account_fee_collection=enabled" in text
    assert (
        'collect-trade-xyz-account-fee --user-address "${SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS}"'
        in text
    )
    assert "--user-address <redacted>" in text
    assert "after_prereqs_command=" in text
    assert "continue_quote_collection_without_archive_or_account_fee_command=" in text
    assert "SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT=0" in text
    assert "SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE=0" in text
    assert "final_readiness_command=" in text
    assert "status_command+=(--fail-on-archive-preflight)" in text
    assert "status_command+=(--fail-on-account-fee-missing)" in text


def test_trade_xyz_until_ready_wrapper_propagates_required_data_prereqs() -> None:
    text = _read("scripts/collect_trade_xyz_data_until_ready.sh")

    assert "SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT:-1" in text
    assert "SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE:-1" in text
    assert "require_archive_preflight=%s" in text
    assert "require_account_fee=%s" in text
    assert "prerequisite_status_command+=(--fail-on-archive-preflight)" in text
    assert "prerequisite_status_command+=(--fail-on-account-fee-missing)" in text
    assert 'if [[ "${collector_running}" != "true" ]]; then' in text
    assert (
        "external prerequisite failures are reported but do not stop organic quote collection"
        in text
    )
