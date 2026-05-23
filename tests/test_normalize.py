from sis.storage.normalize import collect_quote_logs, normalize_quotes


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


def test_normalize_quotes_handles_late_float_after_nulls(tmp_path) -> None:
    raw_path = tmp_path / "raw/gtrade/2026-05-22.jsonl"
    raw_path.parent.mkdir(parents=True)
    rows = []
    base = (
        '{{"ts_client":"2026-05-22T00:{minute:02d}:00Z","venue":"gtrade","canonical_symbol":"SPY",'
        '"venue_symbol":"SPY/USD","pair_index":86,"source":"test","raw_payload_sha256":"{hash}",'
        '"oracle_price":{oracle_price}}}\n'
    )
    for minute in range(150):
        rows.append(
            base.format(
                minute=minute % 60,
                hash=f"hash-{minute}",
                oracle_price="null",
            )
        )
    rows.append(
        base.format(
            minute=59,
            hash="hash-150",
            oracle_price="7464.63333",
        )
    )
    raw_path.write_text("".join(rows), encoding="utf-8")

    count = normalize_quotes(tmp_path / "raw", tmp_path / "normalized/quotes.parquet", tmp_path / "normalized/sis.duckdb")

    assert count == 151
    assert (tmp_path / "normalized/quotes.parquet").exists()
