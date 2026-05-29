# Next Implementation Plan After P0-P1 2026-05-28

この文書は、P0-P1 の混在除去後に次へ進むための実装計画です。

> Current status: implemented. The `Pre-Implementation Gate Snapshot` section below is the snapshot that motivated the work. Use `Implementation Result 2026-05-28` and `data/ops/phase_gate_review_summary.json` for the current state.

## 結論

実装前に次にやることだったのは、機能追加ではなく **P2 に入る前の gate restore** です。

実装前の `validate-artifacts --strict` は通っていました。つまり、当時の問題は schema / artifact existence ではありませんでした。当時の主 blocker は、Trade[XYZ] の対象 5 銘柄すべてで `fee_mode_unknown_rate=1.0` が残っていることでした。

したがって、実装順序は次のとおりです。

1. Trade[XYZ] の `fee_mode` を銘柄別に確定する。
2. registry / quote / diagnostics / phase gate に fee mode を反映する。
3. `phase-gate-review` を再実行し、fee unknown blocker が消えたことを確認する。
4. execution drift を P2 blocker と live-readiness blocker に分離する。
5. Alpaca provider と real-market / tracking layer を P2 として進める。

wallet、signing、exchange write API、public micro live CLI、production live trading はまだやらない。

## Pre-Implementation Gate Snapshot

2026-05-28 の P2-00 実装前に確認した values:

```text
validate-artifacts --strict:
  checked_files: 11
  issues: 0

phase-gate-review:
  phase_gate_decision: NO_GO
  phase2_entry_allowed: false
  diagnostics_symbols:
    - SP500
    - XYZ100
    - NVDA
    - AAPL
    - MSFT
  blockers:
    - SP500:fee_mode_unknown_rate=1.0
    - XYZ100:fee_mode_unknown_rate=1.0
    - NVDA:fee_mode_unknown_rate=1.0
    - AAPL:fee_mode_unknown_rate=1.0
    - MSFT:fee_mode_unknown_rate=1.0
```

読み方:

- `strict_validation_issue_count=0` は、Trade[XYZ] strict artifact chain が壊れていないという意味。
- `phase_gate_decision=NO_GO` は、強化後の quote quality gate が `fee_mode_unknown_rate` を blocker として止めているという意味。
- `fee_mode_unknown_rate=1.0` は、read-only quote collection の失敗ではなく、paper / micro live / P2 gate 前の fee certainty failure として扱う。

## Implementation Result 2026-05-28

この計画の P2-00 から P2-05 までの実装後 state:

```text
validate-artifacts --strict:
  checked_files: 12
  issues: 0

phase-gate-review:
  phase_gate_decision: READ_ONLY_GO
  phase2_entry_allowed: true
  blockers: []
  diagnostics_symbols:
    - SP500
    - XYZ100
    - NVDA
    - AAPL
    - MSFT
  fee_mode_unknown_rate:
    SP500: 0.0
    XYZ100: 0.0
    NVDA: 0.0
    AAPL: 0.0
    MSFT: 0.0
  execution_drift_classification_counts:
    P2_BLOCKER: 0
    LIVE_READINESS_BLOCKER: 6
```

実装済み:

- `configs/fee_model.trade_xyz.yaml` に Trade[XYZ] active symbols の明示 fee classification を追加した。
- `build_trade_xyz_registry()` が config/seed 由来の `fee_mode`, `taker_fee_bps`, `maker_fee_bps` を registry に出す。
- `collect_trade_xyz_quotes()` と `quote_from_l2_book()` が registry fee fields を raw quote row へ伝播する。
- Trade[XYZ] diagnostics / phase gate は latest quote file を current artifact として評価する。過去 JSONL の stale fee unknown は current gate を汚染しない。
- phase gate summary / markdown に `execution_drift_classifications` を出す。現時点の drift は P2 research blocker ではなく live-readiness blocker。
- Alpaca provider は silent `[]` stub ではなく、credentials 未設定なら `AlpacaProviderUnavailable`、成功時は Alpaca stock bars response を `RealMarketBar` に変換する。
- tracking は `mark_price` のみで `mark_real_diff_bps` を計算し、`BLOCK_MISSING_MARK_PRICE`, `BLOCK_LOW_SOURCE_CONFIDENCE`, `BLOCK_UNDERLYING_SESSION_CLOSED`, `BLOCK_FEE_MODE_UNKNOWN` を区別する。

残る制約:

- Alpaca live fetch は credentials が必要。offline unit path は検証済みだが、実 API 成功 path は環境変数なしでは未検証。
- `execution_drift_classification_counts.LIVE_READINESS_BLOCKER=6` は production live readiness の blocker として残す。read-only P2 entry は許可するが、live trading ready とは読まない。

## P2-00 Gate Restore

目的:

P2 に入る前に、P0-P1 で強化した gate を current artifact で通せる状態へ戻す。

変更対象:

- `configs/fee_model.trade_xyz.yaml`
- `src/sis/venues/trade_xyz/registry.py`
- `src/sis/venues/trade_xyz/collector.py`
- `src/sis/venues/trade_xyz/normalizer.py`
- `src/sis/reports/quote_diagnostics.py`
- `src/sis/reports/phase_gate_review.py`

やること:

- `fee_model.trade_xyz.yaml` の `fallback.growth` / `fallback.standard` を fee mode 判定の正本として扱う。
- registry row に `fee_mode`, `taker_fee_bps`, `maker_fee_bps` を入れる。
- quote row に registry 由来の fee fields を伝播する。
- diagnostics で `fee_mode_unknown_rate == 0` になることを確認する。
- phase gate が fee unknown blocker では止まらない状態にする。

完了条件:

- `data/registry/trade_xyz_instrument_registry.json` の対象 5 銘柄に `fee_mode != unknown` が入る。
- raw quote JSONL の対象 5 銘柄に `fee_mode != unknown` が入る。
- quote diagnostics summary で対象 5 銘柄の `fee_mode_unknown_rate == 0`。
- `uv run sis validate-artifacts --strict` が `issues=0`。
- `uv run sis phase-gate-review` が fee unknown blocker を出さない。

Stop condition:

- fee mode を根拠なしに一律 `standard` へ固定する必要が出た場合は止める。
- `configs/fee_model.trade_xyz.yaml` と registry artifact の fee bps が矛盾した場合は止める。
- fee mode を消すためだけに phase gate 条件を緩める変更はしない。

Verification:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
./scripts/check
```

## P2-01 Fee Mode Resolution

目的:

Trade[XYZ] の銘柄ごとに fee mode と fee bps を再生成可能にする。

期待する実装:

- `InstrumentSpec` の `fee_mode`, `taker_fee_bps`, `maker_fee_bps` を registry build 時に埋める。
- seed / config / observed source のどれを使ったかを `notes` または明示 field に残す。
- collector / normalizer は registry の fee fields を quote row へ渡す。
- paper cost model は quote row の explicit fee bps を優先し、無ければ config fallback を使う。

最小 acceptable path:

- まずは `configs/fee_model.trade_xyz.yaml` の `fallback.standard` / `fallback.growth` を使い、対象 5 銘柄を明示分類する。
- 分類根拠が未確定の銘柄は `unknown` のまま残し、phase gate が止める。

完了条件:

- 対象 5 銘柄の registry row に `fee_mode`, `taker_fee_bps`, `maker_fee_bps` がある。
- `tests/test_trade_xyz_registry.py` に fee mode propagation test がある。
- `tests/test_trade_xyz_collector.py` または normalizer test に quote row propagation test がある。
- `tests/test_phase_gate_review.py` に fee unknown が blocker になる test と、fee known なら blocker にならない test がある。

Stop condition:

- external API から fee tier を取得できる前提にして実装が詰まる場合は、まず config-driven explicit classification に戻す。
- unknown を silent fallback で standard 扱いしない。

## P2-02 Phase Gate Recheck

目的:

P2-00 / P2-01 の結果を gate artifact として閉じる。

やること:

- `phase-gate-review` を再実行する。
- `data/ops/phase_gate_review_summary.json` の blocker を読む。
- `fee_mode_unknown_rate` が消えた後に残る blocker を次の failure mode へ分類する。

完了条件:

- `fee_mode_unknown_rate=1.0` blocker が消えている。
- `phase_gate_decision` が `READ_ONLY_GO`、または残 blocker が fee mode 以外として明示されている。
- `data/reports/phase_gate_review.md` の Diagnostics table が `fee_mode_unknown_rate` を表示している。
- `next implementation blocker` が 1 つの failure mode に分類されている。

Stop condition:

- `phase_gate_decision=READ_ONLY_GO` になっても、execution drift degraded を production live readiness と読まない。
- `next_actions=[]` を「live trading ready」と読まない。

Verification:

```bash
uv run sis phase-gate-review
jq '{phase_gate_decision, phase2_entry_allowed, blockers, diagnostics_symbols}' data/ops/phase_gate_review_summary.json
```

## P2-03 Execution Drift Classification

目的:

execution drift degraded を P2 の research blocker と live-readiness blocker に分ける。

実装前の現状:

- `phase-gate-review` は execution drift degraded を表示する。
- ただし、これは read-only quote gate と同じ failure mode ではない。

やること:

- `execution_drift_overview_status`, `execution_balance_gap_detected`, `execution_fills_gap_detected` を読む。
- P2 research layer に必要なものと、live execution readiness にしか必要ないものを分ける。
- P2 入りを止める条件を `docs/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md` または後続 doc に反映する。

完了条件:

- execution drift の各 degraded reason が次のどちらかに分類されている。
  - `P2_BLOCKER`
  - `LIVE_READINESS_BLOCKER`
- `phase-gate-review` の `NO_GO` 理由と execution drift の degraded 理由を混同しない説明がある。
- `refresh-operations-artifacts` 後に drift summary が再生成される。

Stop condition:

- balance / fills / order status の不足を P2 research layer の blocker として扱い始めた場合は止める。
- 逆に、tracking / source confidence に必要な data drift を live-only として無視しない。

Verification:

```bash
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

## P2-04 Alpaca Provider

目的:

`src/sis/real_market/providers/alpaca.py` の stub を解消し、real-market data layer を本当に使える状態にする。

現状:

```text
fetch_alpaca_bars(...): return []
```

やること:

- Alpaca credentials が無い場合は、明示的 unavailable result / controlled failure にする。
- credentials がある場合は、対象 symbol / timeframe の bars を取得する。
- provider name、request window、row count、failure reason を artifact に残す。
- yfinance / stooq などの fallback と同じ信頼度で混ぜない。

完了条件:

- Alpaca provider が silent empty list を返さない。
- 成功時は `RealMarketBar` rows を返す。
- 失敗時は operator が原因を読める。
- source confidence に provider 種別が反映される。
- provider test は network required path と offline/unit path を分ける。

Stop condition:

- API key / secret を repo に書く必要が出た場合は止める。
- provider failure を empty data として silent pass させない。
- fallback provider を使った場合、artifact に fallback provenance が残らないなら止める。

Verification:

```bash
uv run pytest tests/test_real_market_models.py tests/test_real_market_quality.py tests/test_real_market_features.py -q
uv run sis ingest-research-data
uv run sis check-research-quality
```

## P2-05 Real Market / Tracking Completion

目的:

real-market data と Trade[XYZ] venue quote を、tracking gate で安全に比較できる状態にする。

やること:

- real-market provider artifact を feature panel に接続する。
- `source_confidence` を provider / fallback / missing data に応じて決める。
- `mark_real_diff_bps` は `mark_price` のみを使う。`mid_price` 代用は禁止。
- underlying session と venue book status を混同しない。
- tracking blocker を report に残す。

完了条件:

- `uv run sis build-feature-panel` が対象 symbols の feature artifact を出す。
- `uv run sis build-signals` が feature artifact から再生成できる。
- `uv run sis check-research-quality` が row count / missing rate / source confidence を出す。
- tracking record は `BLOCK_MISSING_MARK_PRICE`, `BLOCK_LOW_SOURCE_CONFIDENCE`, `BLOCK_UNDERLYING_SESSION_CLOSED`, `BLOCK_FEE_MODE_UNKNOWN` を区別する。
- `tests/test_real_vs_venue_tracking.py` が mark-only diff、source confidence、session blocker を検査する。

Stop condition:

- venue mid と mark を同じ truth として扱う必要が出た場合は止める。
- underlying session が unknown のまま `trade_allowed=true` へ進む場合は止める。
- feature panel の欠損を signal builder 側で silent skip する場合は止める。

Verification:

```bash
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
uv run pytest tests/test_real_vs_venue_tracking.py tests/test_tracking_models.py tests/test_lead_lag.py -q
./scripts/check
```

## Completion Criteria

## Restart Plan After A5

この節は `./.ai_memory/HANDOFF.md` の 2026-05-29 restart contract に基づく、A5 以降の実行計画です。古い chat transcript や過去ログは前提にしません。

### A5 Repository Health Gate

目的:

新しい実装に入る前に、repo 全体の health gate を再確認する。

実行:

```bash
./scripts/check
```

期待値:

- Python `3.13.7`
- `ruff` pass
- `pyrefly` 0 errors
- `pytest` 294 passed

Stop condition:

- `./scripts/check` が失敗した場合は、以降の新規実装に進まず、最小失敗単位を特定する。
- 失敗原因が generated artifact の鮮度だけなら、該当 artifact の再生成コマンドを明記してから再実行する。
- unrelated な docs/algo 変更や user-owned 変更は revert しない。

### After A5: Live Readiness Blocker Decomposition

現時点の境界:

- read-only Phase 2 entry は green。
- `phase-gate-review` は `READ_ONLY_GO`。
- `phase2_entry_allowed=True`。
- `P2_BLOCKER=0`。
- `LIVE_READINESS_BLOCKER=6`。
- live order submission、exchange write API、wallet / signing work はまだ対象外。

A5 後にやることは、`LIVE_READINESS_BLOCKER=6` を production live readiness の blocker として分解すること。read-only P2 entry の blocker と混同しない。

分解対象:

1. live execution readiness cleanup
2. execution adapter coverage
3. balance / fills gap resolution
4. execution state comparison mismatch resolution
5. snapshot drift mismatch resolution
6. policy 上必要な場合の fresh Alpaca source confidence pass

### B1 Live Readiness Blocker Inventory

目的:

6 個の live-readiness blocker を、現在の artifact から named blocker と named file に落とす。

読むもの:

```bash
jq '.' data/ops/phase_gate_review_summary.json
jq '.' data/ops/execution_drift_overview_summary.json
jq '.' data/ops/execution_venue_diagnostics_summary.json
jq '.' data/ops/execution_venue_comparison_summary.json
jq '.' data/ops/execution_state_comparison_history_summary.json
jq '.' data/ops/execution_snapshot_drift_history_summary.json
```

完了条件:

- 各 blocker が `signal`, `observed`, `expected`, `source artifact`, `likely owning code path` を持つ。
- `P2_BLOCKER` と `LIVE_READINESS_BLOCKER` を混同しない。
- docs または generated report に blocker inventory が残る。

Stop condition:

- live-readiness blocker を消すために phase gate 条件を緩める必要が出た場合は止める。
- balance / fills / order state の不足を read-only P2 blocker として扱い始めた場合は止める。

### B2 Execution Adapter Coverage

目的:

live execution readiness に必要な execution adapter の coverage gap を、コードと tests で特定する。

読むもの:

- `src/sis/execution/`
- `tests/test_trade_xyz_adapter_safety.py`
- `tests/test_micro_live_canary.py`
- `tests/test_trade_xyz_live_order_policy.py`

完了条件:

- adapter が read-only / dry-run / live write boundary を明示している。
- uncovered live-readiness behavior が test 名付きで分かる。
- public CLI surface に live order execution を exposed しない。

Stop condition:

- 実取引 API write、wallet、signing、secret の投入が必要になった場合は止める。

### B3 Balance / Fills Gap Resolution

目的:

`execution_balance_gap_detected=True` と `execution_fills_gap_detected=True` の原因を、artifact 不足、比較ロジック不一致、または adapter 未接続に分類する。

読むもの:

```bash
jq '.' data/ops/execution_snapshot_summary.json
jq '.' data/ops/execution_gap_history_summary.json
jq '.' data/ops/execution_venue_diagnostics_summary.json
```

完了条件:

- balance gap と fills gap の expected source が明記されている。
- current run で missing なのか、historical comparison で mismatch なのかが分かる。
- 解消案が artifact regeneration、code fix、policy decision のいずれかに分類されている。

Stop condition:

- missing balance / fills を dummy data で埋める必要が出た場合は止める。

### B4 State Comparison And Snapshot Drift Cleanup

目的:

`execution_state_comparison_mismatching_count=3` と `execution_snapshot_drift_mismatching_snapshot_count=3` を、どの snapshot / state がずれているかまで分解する。

読むもの:

```bash
jq '.' data/ops/execution_state_comparison_history_summary.json
jq '.' data/ops/execution_snapshot_drift_history_summary.json
jq '.' data/ops/execution_drift_overview_summary.json
```

完了条件:

- mismatch 3 件の具体的な field / artifact / timestamp が分かる。
- snapshot drift が expected policy change なのか regression なのか分類されている。
- 修正する場合は、先に failing targeted test または reproducible artifact comparison を用意する。

Stop condition:

- historical artifact を根拠なく書き換える必要が出た場合は止める。

### B5 Fresh Alpaca Source Confidence Pass

目的:

policy 上必要な場合だけ、Alpaca source confidence を fresh bar で再確認する。

前提:

- credentials なしの controlled failure と、credentials ありの provider connectivity / data availability は別物として扱う。
- historical IEX bar の success は fresh live `status=pass` と同義ではない。

完了条件:

- provider connectivity、data availability、live suitability のどれが pass / blocked か分かる。
- `BLOCK_LOW_SOURCE_CONFIDENCE` または `BLOCK_ALPACA_NO_BARS` が残る場合、market session / request window / provider response が artifact に残る。

Stop condition:

- API key / secret を repo、docs、logs に書く必要が出た場合は止める。
- fallback provider を primary truth として silent 採用する必要が出た場合は止める。

### B6 Verification Closeout

目的:

live-readiness blocker の分解または修正後に、read-only Phase 2 entry と live-readiness 境界が維持されていることを確認する。

実行:

```bash
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
./scripts/check
```

期待値:

- strict validation は `issues=0`。
- read-only Phase 2 entry は `READ_ONLY_GO` / `phase2_entry_allowed=True` を維持する。
- live-readiness blocker が残る場合は、`LIVE_READINESS_BLOCKER` として残り、P2 blocker に混ざらない。
- live-readiness blocker を解消した場合でも、live order submission は別 gate として扱う。

Stop condition:

- `LIVE_READINESS_BLOCKER=0` だけを根拠に production live trading ready と判断しない。
- live order submission、exchange write API、wallet / signing work へ進まない。

### P2前 Gate Restore 完了

次をすべて満たすこと。

- `uv run sis validate-artifacts --strict` が `issues=0`
- `uv run sis phase-gate-review` が `fee_mode_unknown_rate` blocker を出さない
- target symbols は `SP500`, `XYZ100`, `NVDA`, `AAPL`, `MSFT`
- legacy gTrade/Ostium/XAU fallback が default gate に戻っていない
- `data/ops/phase_gate_review_summary.json` の blocker が fee mode 以外なら、その failure mode が明記されている

### Phase 2 完了

次をすべて満たすこと。

- real-market provider が silent stub ではない
- market / event / feature / signal artifact が再生成できる
- source confidence が provider provenance と連動している
- tracking gate が venue quote と real-market truth の差分を blocker として出せる
- `./scripts/check` が通る
- P2 完了 report が `docs/` または `data/reports/` に残る

## Do Not Do Yet

次はこの計画の対象外です。

- wallet 接続
- signing
- exchange write API
- public micro live CLI
- production live trading
- fee unknown を無視するための phase gate 緩和
- yfinance / fallback provider を primary truth として silent 採用
- XAU / WTI / FX / pure crypto の active surface 復活

## Verification Bundle

P2前 gate restore:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
./scripts/check
```

P2 implementation:

```bash
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
uv run pytest tests/test_real_market_models.py tests/test_real_market_quality.py tests/test_real_market_features.py tests/test_real_vs_venue_tracking.py tests/test_tracking_models.py tests/test_lead_lag.py -q
./scripts/check
```

## Existing Docs Relationship

- `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-27.md`: 判断軸。壊れ方単位で読む。
- `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md`: P0-P1 前の棚卸し。現 gate は強化済みなので、数値は再確認して読む。
- `docs/ARCHITECTURE_AND_PHASES.md`: subsystem / phase の概要。
- `docs/OPERATIONS_RUNBOOK.md`: 再生成コマンドの入口。
- `docs/archive/2026-05-25-doc-refresh/PHASE2_COMPLETION_DEFINITION.md`: 古い Phase 2 参考資料。`QQQ / SPY / XAU` 前提が残るため、現行正本にはしない。
