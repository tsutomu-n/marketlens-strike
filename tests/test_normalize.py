from sis.storage.normalize import collect_quote_logs


def test_collect_quote_logs_deduplicates_replayed_rows(tmp_path) -> None:
    raw_path = tmp_path / "gtrade/2026-05-22.jsonl"
    raw_path.parent.mkdir(parents=True)
    line = (
        '{"ts_client":"2026-05-22T00:00:00Z","venue":"gtrade",'
        '"canonical_symbol":"SPY","venue_symbol":"SPY/USD",'
        '"source":"test","raw_payload_sha256":"abc123"}\n'
    )
    raw_path.write_text(line + line, encoding="utf-8")

    logs = collect_quote_logs(tmp_path)

    assert len(logs) == 1
