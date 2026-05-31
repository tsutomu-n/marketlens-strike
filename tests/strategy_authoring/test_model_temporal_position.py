# ruff: noqa: F403,F405

from .helpers import *  # noqa: F403,F405


def test_authoring_model_score_builds_raw_score_without_weighted_sum(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "model_score.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            """  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
      - column: research_return_4h
        weight: 5
""",
            """  score:
    model_score:
      model_type: linear
      intercept: 0.1
      activation: clamp_0_1
      missing_value: 0.0
      coefficients:
        - column: research_return_1d
          weight: 20
        - column: source_confidence
          weight: 0.5
""",
        ),
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("raw_score").to_list() == pytest.approx([0.9, 0.9, 0.9])
    assert frame.get_column("rank_score").to_list() == pytest.approx([0.9, 0.9, 0.9])


def test_authoring_model_score_reports_missing_feature_column(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "model_score.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            """  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
      - column: research_return_4h
        weight: 5
""",
            """  score:
    model_score:
      coefficients:
        - column: missing_model_feature
          weight: 1
""",
        ),
        encoding="utf-8",
    )

    errors = validate_authoring_inputs(load_authoring_spec(spec_path), data_dir=data_dir)

    assert errors
    assert "missing_model_feature" in errors[0]


def test_strategy_authoring_train_model_writes_model_score_and_spec(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    out_spec = tmp_path / "trained_authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_spec(spec_path)
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index, (x_value, y_value) in enumerate([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (2.0, 1.0)]):
        rows.append(
            {
                **_feature_rows()[0],
                "ts": start + timedelta(hours=index),
                "research_return_1d": x_value,
                "source_confidence": y_value,
                "target_forward_return": 0.5 + 2.0 * x_value - y_value,
            }
        )
    pl.DataFrame(rows).write_parquet(feature_path)

    result = runner.invoke(
        app,
        [
            "strategy-author-train-model",
            "--spec",
            str(spec_path),
            "--target-column",
            "target_forward_return",
            "--feature-column",
            "research_return_1d",
            "--feature-column",
            "source_confidence",
            "--ridge-lambda",
            "0",
            "--out-spec",
            str(out_spec),
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (data_dir / "research/strategy_authoring_model_score.json").read_text(encoding="utf-8")
    )
    assert payload["paper_only"] is True
    assert payload["live_order_submitted"] is False
    assert payload["row_count"] == 4
    assert payload["model_score"]["intercept"] == pytest.approx(0.5)
    weights = {item["column"]: item["weight"] for item in payload["model_score"]["coefficients"]}
    assert weights == pytest.approx({"research_return_1d": 2.0, "source_confidence": -1.0})
    trained_spec = load_authoring_spec(out_spec)
    assert trained_spec.rules.score.model_score is not None
    assert trained_spec.rules.score.model_score.intercept == pytest.approx(0.5)


def test_authoring_temporal_rules_block_out_of_schedule_and_cooldown(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "temporal.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n  temporal:\n    allowed_weekdays_utc: [3]\n    allowed_hours_utc: [0, 4]\n    cooldown_minutes: 300\n    max_signals_per_symbol_per_day: 1",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    trade_rows = frame.filter(pl.col("side") != "none")
    blocked_rows = frame.filter(pl.col("side") == "none")
    assert trade_rows.height == 1
    assert blocked_rows.get_column("block_reasons").to_list() == [
        ["temporal_cooldown"],
        ["temporal_hour_filter"],
    ]


def test_authoring_temporal_validation_rejects_invalid_hour(tmp_path) -> None:
    spec_path = tmp_path / "temporal.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n  temporal:\n    allowed_hours_utc: [24]",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="allowed_hours_utc"):
        load_authoring_spec(spec_path)


def test_authoring_position_rules_block_overlapping_symbol_entries(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  position:\n"
            "    max_open_signals_per_symbol: 1\n"
            "    holding_horizon_minutes: 480",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "none", "long"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["position_open_signal_limit"]
    ]


def test_authoring_position_rules_close_marker_releases_open_state(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-close.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  close:\n    all:\n      - column: close_signal\n        op: is_true\n"
            "  entry:\n    none:\n      - column: close_signal\n        op: is_true\n    all:",
        )
        .replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  position:\n"
            "    max_open_signals_per_symbol: 1\n"
            "    holding_horizon_minutes: 480",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {**_feature_rows()[0], "ts": start, "close_signal": False},
        {**_feature_rows()[1], "ts": start + timedelta(hours=1), "close_signal": True},
        {**_feature_rows()[2], "ts": start + timedelta(hours=2), "close_signal": False},
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "close", "long"]
    assert frame.filter(pl.col("side") == "none").is_empty()


def test_authoring_position_rules_can_require_open_position_for_markers(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-require-marker.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  reduce:\n    all:\n      - column: reduce_signal\n        op: is_true\n"
            "  entry:\n    none:\n      - column: reduce_signal\n        op: is_true\n    all:",
        )
        .replace(
            "exit:\n    stop_loss_bps: 150",
            "exit:\n    exit_on_reduce_signal: true\n    reduce_fraction: 0.5\n    stop_loss_bps: 150",
        )
        .replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  position:\n"
            "    require_open_position_for_markers: true",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {**_feature_rows()[0], "ts": start, "reduce_signal": True},
        {**_feature_rows()[1], "ts": start + timedelta(hours=1), "reduce_signal": False},
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["none", "long"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["position_marker_without_open"]
    ]


def test_authoring_position_rules_can_block_opposing_open_positions(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-no-opposing.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("  side: long\n", "  side: auto\n  side_column: direction\n")
        .replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  position:\n"
            "    allow_opposing_open_positions: false",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {**_feature_rows()[0], "ts": start, "direction": "long"},
        {**_feature_rows()[1], "ts": start + timedelta(hours=1), "direction": "short"},
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "none"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["position_opposing_open_position"]
    ]


def test_authoring_position_rules_can_block_same_side_pyramiding(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-no-pyramiding.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  position:\n"
            "    allow_pyramiding: false",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {**_feature_rows()[0], "ts": start},
        {**_feature_rows()[1], "ts": start + timedelta(hours=1)},
        {**_feature_rows()[2], "ts": start + timedelta(hours=2)},
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "none", "none"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["position_pyramiding_not_allowed"],
        ["position_pyramiding_not_allowed"],
    ]


def test_authoring_event_window_allow_blocks_outside_or_missing_event(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "event-window.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    rows[0]["earnings_ts"] = (rows[0]["ts"] + timedelta(minutes=30)).isoformat()
    rows[1]["earnings_ts"] = (rows[1]["ts"] + timedelta(hours=2)).isoformat()
    rows[2]["earnings_ts"] = None
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  event_windows:\n"
            "    - name: earnings_pre\n"
            "      event_ts_column: earnings_ts\n"
            "      mode: allow\n"
            "      before_minutes: 60\n"
            "      after_minutes: 0\n"
            "      block_reason: event_pre_earnings",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.filter(pl.col("side") != "none").height == 1
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["event_pre_earnings_outside"],
        ["event_pre_earnings_missing"],
    ]


def test_authoring_event_window_block_blocks_inside_blackout(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "event-blackout.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    rows[0]["macro_ts"] = (rows[0]["ts"] + timedelta(minutes=15)).isoformat()
    rows[1]["macro_ts"] = (rows[1]["ts"] + timedelta(hours=2)).isoformat()
    rows[2]["macro_ts"] = None
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  event_windows:\n"
            "    - name: macro_blackout\n"
            "      event_ts_column: macro_ts\n"
            "      mode: block\n"
            "      before_minutes: 30\n"
            "      after_minutes: 30",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.filter(pl.col("side") != "none").height == 2
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["event_window_macro_blackout"],
    ]
