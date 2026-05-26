from sis.storage.jsonl_store import write_json
from sis.venues.archive.ostium.positions import (
    latest_positions_sidecar,
    positions_have_liquidation_reference,
)


def test_positions_have_liquidation_reference_requires_real_position_rows(tmp_path) -> None:
    positions_path = tmp_path / "positions_0xabc_2026-05-22.json"
    write_json(
        positions_path,
        {
            "positions": [
                {
                    "venue_symbol": "XAU-USD",
                    "side": "long",
                    "entry_px": "2400",
                    "liquidation_px": "2200",
                }
            ]
        },
    )

    assert positions_have_liquidation_reference(positions_path) is True


def test_positions_have_liquidation_reference_rejects_empty_probe(tmp_path) -> None:
    positions_path = tmp_path / "positions_0xabc_2026-05-22.json"
    write_json(positions_path, {"positions": []})

    assert positions_have_liquidation_reference(positions_path) is False


def test_latest_positions_sidecar_returns_newest_file(tmp_path) -> None:
    old_path = tmp_path / "positions_0xabc_2026-05-21.json"
    new_path = tmp_path / "positions_all_2026-05-22.json"
    write_json(old_path, {"positions": []})
    write_json(new_path, {"positions": []})

    assert latest_positions_sidecar(tmp_path) == new_path
