from __future__ import annotations

import pytest

from sis.reports.cost_matrix_metadata import (
    as_bps_from_gtrade_fee,
    as_float,
    gtrade_holding_bps,
    latest_gtrade_sidecar,
    metadata_rows,
    worst_abs_ostium_rollover_bps,
)


def test_latest_gtrade_sidecar_uses_sorted_filename_order(tmp_path) -> None:
    sidecar_root = tmp_path / "raw/sidecar/gtrade"
    sidecar_root.mkdir(parents=True)
    older = sidecar_root / "2026-05-21.jsonl"
    newer = sidecar_root / "2026-05-22.jsonl"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")

    assert latest_gtrade_sidecar(sidecar_root) == newer
    assert latest_gtrade_sidecar(tmp_path / "missing") is None
    assert latest_gtrade_sidecar(None) is None


def test_numeric_conversion_helpers() -> None:
    assert as_float(True) is None
    assert as_float(" 1.25 ") == 1.25
    assert as_float("bad") is None
    assert as_bps_from_gtrade_fee("350000000") == 3.5
    assert worst_abs_ostium_rollover_bps("-0.01", "0.02", 4) == 1.0
    assert worst_abs_ostium_rollover_bps(None, None, 4) is None


def test_gtrade_holding_bps_uses_active_collateral_max_borrowing_and_funding() -> None:
    pair = {"pair_index": 90}
    snapshot = {
        "raw": {
            "collaterals": [
                {
                    "isActive": True,
                    "borrowingFees": {
                        "v2": {"pairParams": {"90": {"borrowingRatePerSecondP": "100"}}}
                    },
                    "fundingFees": {
                        "pairParams": {"90": {"fundingFeesEnabled": True}},
                        "pairData": {"90": {"lastFundingRatePerSecondP": "200000000"}},
                    },
                }
            ]
        }
    }

    assert gtrade_holding_bps(pair, snapshot, 4) == 0.0432
    assert gtrade_holding_bps(pair, snapshot, 72) == pytest.approx(0.7776)
    assert gtrade_holding_bps({}, snapshot, 4) is None


def test_metadata_rows_overlay_sidecar_and_registry_metadata(tmp_path) -> None:
    gtrade_sidecar_root = tmp_path / "raw/sidecar/gtrade"
    ostium_registry_path = tmp_path / "registry/ostium_instrument_registry.json"
    gtrade_sidecar_root.mkdir(parents=True)
    ostium_registry_path.parent.mkdir(parents=True)
    (gtrade_sidecar_root / "2026-05-22.jsonl").write_text(
        '{"pairs":[{"canonical_symbol":"XAU","spread_bps":0,'
        '"pair_index":90,"fee_index":"13","total_position_size_fee_p":"350000000"}],'
        '"raw":{"collaterals":[{"isActive":true,'
        '"borrowingFees":{"v2":{"pairParams":{"90":{"borrowingRatePerSecondP":"100"}}}},'
        '"fundingFees":{"pairParams":{"90":{"fundingFeesEnabled":true}},'
        '"pairData":{"90":{"lastFundingRatePerSecondP":"200000000"}}}}]}}\n',
        encoding="utf-8",
    )
    ostium_registry_path.write_text(
        '[{"venue":"ostium","canonical_symbol":"XAU","opening_fee_bps":3,'
        '"rollover_fee_per_block":"1.2e-10","rollover_rate_long":"-0.01",'
        '"rollover_rate_short":"0.02"}]',
        encoding="utf-8",
    )

    rows = metadata_rows(
        gtrade_sidecar_root=gtrade_sidecar_root,
        ostium_registry_path=ostium_registry_path,
    )
    gtrade_xau = next(row for row in rows if row["venue"] == "gtrade" and row["symbol"] == "XAU")
    ostium_xau = next(row for row in rows if row["venue"] == "ostium" and row["symbol"] == "XAU")

    assert gtrade_xau["open_fee_bps"] == 3.5
    assert gtrade_xau["close_fee_bps"] == 3.5
    assert gtrade_xau["holding_cost_4h_bps"] == 0.0432
    assert "fee_index=13" in gtrade_xau["notes"]
    assert ostium_xau["open_fee_bps"] == 3.0
    assert ostium_xau["holding_cost_4h_bps"] == 1.0
    assert ostium_xau["holding_cost_72h_bps"] == 18.0
    assert "rollover_rate_long=-0.01" in ostium_xau["notes"]
