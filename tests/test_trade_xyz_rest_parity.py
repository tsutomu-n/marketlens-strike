from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from sis.venues.trade_xyz.rest_parity import build_trade_xyz_rest_parity_manifest


class _FakeClient:
    def all_mids(self):
        return {"xyz:SP500": "100.0"}

    def meta_and_asset_ctxs(self):
        return {}, [{"coin": "xyz:SP500"}]

    def perps_at_open_interest_cap(self):
        return []

    def perp_dex_status(self):
        return {"status": "ok"}

    def perp_dex_limits(self):
        return {"limits": {}}

    def l2_book(self, _coin: str):
        return {"levels": [[], []]}


def test_build_trade_xyz_rest_parity_manifest(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    ws_manifest_path = data_dir / "manifests/trade_xyz_ws_capture_manifest.json"
    ws_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    ws_manifest_path.write_text(
        json.dumps({"symbols": ["SP500"]}),
        encoding="utf-8",
    )
    manifest = build_trade_xyz_rest_parity_manifest(
        data_dir=data_dir,
        ws_manifest_path=ws_manifest_path,
        symbols=["SP500"],
        client=_FakeClient(),
        request_delay_seconds=0.0,
        include_l2_book=False,
    )
    assert manifest["status"] == "pass"
    assert manifest["missing_rest_symbols"] == []
    assert manifest["request_error_count"] == 0
    schema = json.loads(
        Path("schemas/trade_xyz_rest_parity_manifest.v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=manifest, schema=schema)
