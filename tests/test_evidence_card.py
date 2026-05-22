import json

from sis.reports.evidence import build_evidence_card
from sis.storage.jsonl_store import write_json


def test_evidence_card_reflects_current_go_no_go_report(tmp_path) -> None:
    data_dir = tmp_path / "data"
    write_json(
        data_dir / "registry/gtrade_instrument_registry.json",
        [{"venue": "gtrade", "canonical_symbol": "SPY"}],
    )
    write_json(
        data_dir / "registry/ostium_instrument_registry.json",
        [
            {
                "venue": "ostium",
                "canonical_symbol": "SPX_EQUIV",
                "venue_symbol": "US500-USD",
                "active": True,
                "opening_fee_bps": 3,
                "max_open_interest": "1000000",
                "rollover_fee_per_block": "1e-10",
                "max_leverage": 50,
            }
        ],
    )
    write_json(
        data_dir / "raw/sidecar/ostium/positions_all_2026-05-22.json",
        {
            "positions": [
                {
                    "venue_symbol": "US500-USD",
                    "side": "long",
                    "entry_px": "100",
                    "liquidation_px": "80",
                }
            ]
        },
    )
    (data_dir / "raw/quotes/gtrade").mkdir(parents=True)
    (data_dir / "raw/quotes/gtrade/2026-05-22.jsonl").write_text('{"venue":"gtrade"}\n')
    (data_dir / "normalized").mkdir(parents=True)
    (data_dir / "normalized/quotes.parquet").write_bytes(b"placeholder")
    (data_dir / "research").mkdir(parents=True)
    (data_dir / "research/venue_cost_matrix.csv").write_text(
        "\n".join(
            [
                "venue,symbol,stale_rate,tradable_rate,spread_p90_bps,holding_cost_4h_bps,holding_cost_24h_bps,holding_cost_72h_bps",
                "gtrade,SPY,0,0,2,0,0,0",
            ]
        ),
        encoding="utf-8",
    )
    write_json(
        data_dir / "research/backtest_metrics.json",
        [{"trade_count": 1, "avg_trade_return": 0.1}],
    )
    (data_dir / "research/backtest_report.md").write_text("# Backtest\n", encoding="utf-8")
    (data_dir / "research/go_no_go_report.md").write_text("# Go/No-Go\n", encoding="utf-8")

    card_path = build_evidence_card(data_dir, data_dir / "evidence")

    card = json.loads(card_path.read_text(encoding="utf-8"))
    assert card["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert card["blockers"] == ["tradable_rate at or above threshold"]
    assert "Liquidation reference complete" in [
        item["criterion"] for item in card["criteria"]
    ]
    assert "Ostium liquidation reference requires real open position data" not in json.dumps(card)
