# Failure Mode Responsibility Map 2026-05-28

コード、runtime artifact、直近の docs audit を正として、`marketlens-strike` の責任境界を機能単位ではなく失敗モード単位で切るための current map。

## 結論

2026-05-28 時点では、P2 へ進む read-only chain は green。残っている主な混在リスクは、P2 blocker ではなく live-readiness blocker を P2 blocker と誤読すること、generated report の古い値を current truth と誤読すること、Alpaca live credentials success を未検証のまま実データ確定扱いすること。

Current snapshot:

```text
./scripts/check:
  294 passed

validate-artifacts --strict:
  checked_files: 12
  issues: 0

phase-gate-review:
  phase_gate_decision: READ_ONLY_GO
  phase2_entry_allowed: true
  blockers: []
  diagnostics_symbols: SP500, XYZ100, NVDA, AAPL, MSFT
  execution_drift_classification_counts:
    P2_BLOCKER: 0
    LIVE_READINESS_BLOCKER: 6

Trade[XYZ] target fee fields:
  SP500, XYZ100, NVDA, AAPL, MSFT:
    fee_mode: standard
    taker_fee_bps: 9.0
    maker_fee_bps: 3.0
```

State labels:

| label | 意味 |
|---|---|
| `RESOLVED_GUARD` | 解消済み。再発防止の guard として見る |
| `ACTIVE_P2` | P2 へ進む前に解消が必要 |
| `ACTIVE_LIVE_READINESS` | P2 は進めるが live / paper-to-live 判断では blocker |
| `DEFERRED` | 現段階では仕様上後回し |
| `LEGACY_ARCHIVE` | active surface ではなく履歴・archive として読む |

## 1. Artifact Freshness / Provenance Failure

State: `RESOLVED_GUARD`

壊れ方:

- `data/` 配下の generated artifact が古い。
- summary、raw quote、registry、report が別 run のものとして混ざる。
- PR12 の long-window evidence と latest refresh artifact を同じものとして読む。
- `phase_gate_review_summary.json` だけを見て、元 artifact の鮮度と symbol universe を見ない。

現在状態:

- strict validation は `checked_files=12`, `issues=0`。
- phase gate は `READ_ONLY_GO`, `blockers=[]`。
- latest artifact は current state の確認材料であり、PR12 60-minute evidence の恒久証跡とは別物。

責任 surface:

- `uv run sis collect-trade-xyz-quotes --write-summary --write-report`
- `uv run sis validate-artifacts --strict`
- `uv run sis phase-gate-review`
- `data/ops/trade_xyz_quote_collection_summary.json`
- `data/ops/phase_gate_review_summary.json`

Stop condition:

- required artifact が欠ける。
- `checked_files` が説明なく減る。
- registry / raw quote / summary の symbol set が一致しない。
- latest refresh artifact を PR12 long-window evidence として扱っている。

Recovery / verification:

```bash
uv run sis collect-trade-xyz-quotes --symbols SP500,XYZ100,NVDA,AAPL,MSFT --replace --write-summary --write-report
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

完了条件:

- strict validation が `issues=0`。
- phase gate の `blockers=[]`。
- docs が latest artifact と PR12 long-window evidence を分けて説明している。

## 2. External Source / Market Window Failure

State: `RESOLVED_GUARD`

壊れ方:

- venue API が落ちる、遅い、空 payload を返す。
- underlying market window が閉じて十分な観測 window が取れない。
- 短い refresh を 60-minute smoke の代替として読む。
- provider outage を schema failure や implementation failure と誤診する。

現在状態:

- Trade[XYZ] collector / probe / summary path は active。
- PR12 long-window evidence と latest refresh は別 artifact として読む必要がある。
- market closed と provider failure は code regression とは別の failure mode。

責任 surface:

- `uv run sis probe trade-xyz`
- `uv run sis collect-trade-xyz-quotes --duration-minutes ... --interval-seconds ...`
- `src/sis/market_calendar.py`
- `src/sis/venues/trade_xyz/client.py`
- `src/sis/venues/trade_xyz/collector.py`

Stop condition:

- expected observation window に届かない。
- fetch failure が summary / raw error に残らない。
- market closed と API failure を同じ missing artifact として扱っている。
- latest short refresh を long-window readiness evidence としている。

Recovery / verification:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --symbols SP500,XYZ100,NVDA,AAPL,MSFT --duration-minutes 60 --interval-seconds 60 --normalize --replace --write-summary --write-report
```

完了条件:

- window length、row count、symbol set、failure reason が summary から説明できる。
- 60-minute evidence が必要な判定では short refresh を使わない。

## 3. Venue Identity / Registry Mapping Failure

State: `RESOLVED_GUARD`

壊れ方:

- Trade[XYZ] symbol と HIP-3 `asset_id` がずれる。
- excluded / legacy-looking symbol を active execution candidate として扱う。
- registry が古いまま quote collection に使われる。
- fee fields の source が registry / config / quote row で説明できない。

現在状態:

- active diagnostics symbols は `SP500`, `XYZ100`, `NVDA`, `AAPL`, `MSFT`。
- target symbols は `fee_mode=standard`, `taker_fee_bps=9.0`, `maker_fee_bps=3.0` を持つ。
- legacy gTrade/Ostium/XAU surface は current Trade[XYZ] path の根拠にしない。

責任 surface:

- `uv run sis probe trade-xyz`
- `src/sis/venues/trade_xyz/registry.py`
- `src/sis/venues/trade_xyz/models.py`
- `configs/fee_model.trade_xyz.yaml`
- `data/registry/trade_xyz_instrument_registry.json`

Stop condition:

- `asset_id` が未解決。
- `api_orderable=false` を active candidate として扱う。
- registry と quote summary の symbol universe が一致しない。
- fee source が説明できない。

Recovery / verification:

```bash
uv run sis probe trade-xyz
uv run pytest tests/test_trade_xyz_registry.py tests/test_trade_xyz_collector.py -q
```

完了条件:

- active target universe が docs、registry、latest diagnostics で一致する。
- excluded / legacy symbol が active CLI smoke や gate 根拠に戻らない。

## 4. Quote Quality / Fee Certainty Failure

State: `RESOLVED_GUARD`

壊れ方:

- mark / oracle / funding / open interest が欠ける。
- stale quote、L2-only quote、wide spread を usable quote として扱う。
- side-specific depth ではなく合算 depth だけで判断する。
- `fee_mode_unknown_rate=1.0` を current blocker として誤読する、または再発しても見逃す。

現在状態:

- latest diagnostics は target symbols で `fee_mode_unknown_rate=0.0`。
- phase gate の healthy diagnostic 条件は missing fields、stale、L2-only、fee unknown、spread p90 を見る。
- `fee_mode_unknown_rate=1.0` は current blocker ではなく regression signal。

責任 surface:

- `uv run sis diagnose-quotes --venue trade_xyz`
- `src/sis/venues/trade_xyz/normalizer.py`
- `src/sis/venues/trade_xyz/quality.py`
- `src/sis/reports/quote_diagnostics.py`
- `src/sis/reports/phase_gate_review.py`

Stop condition:

- `missing_mark_price_rate != 0`
- `missing_oracle_price_rate != 0`
- `missing_funding_rate != 0`
- `missing_open_interest_rate != 0`
- `stale_rate != 0`
- `l2_only_rate != 0`
- `fee_mode_unknown_rate != 0`
- `spread_p90_bps` が policy threshold を超える。

Recovery / verification:

```bash
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

完了条件:

- target symbols の diagnostics が healthy。
- fee unknown が再発した場合、`READ_ONLY_GO` へ進まない。

## 5. Schema / Strict Validation Failure

State: `RESOLVED_GUARD`

壊れ方:

- required field が欠ける。
- schema は通るが strict chain の required artifact が欠ける。
- legacy-only artifact で strict validation が pass したように見える。
- raw / normalized / summary / report の contract が片方だけ更新される。

現在状態:

- `validate-artifacts --strict` は Trade[XYZ] artifact を前提に `checked_files=12`, `issues=0`。
- legacy-only pass は current success condition ではない。

責任 surface:

- `uv run sis validate-artifacts --strict`
- `src/sis/validation/artifacts.py`
- `schemas/quote_log_v2.schema.json`
- `schemas/trade_xyz_quote_collection_summary.schema.json`

Stop condition:

- `issues > 0`
- `checked_files` が説明なく減る。
- Trade[XYZ] registry / raw quote / summary / normalized output が欠ける。
- strict validation の根拠が legacy-only artifact になっている。

Recovery / verification:

```bash
uv run sis validate-artifacts --strict
uv run pytest tests/test_validate_artifacts_trade_xyz.py -q
```

完了条件:

- strict validation が Trade[XYZ] chain で pass する。
- checked artifact list が docs / runbook の想定と一致する。

## 6. Gate Interpretation Failure

State: `RESOLVED_GUARD`

壊れ方:

- `READ_ONLY_GO` を production live ready と読む。
- `phase2_entry_allowed=true` を micro live allowed と読む。
- `blockers=[]` を「全リスク解消」と読む。
- execution drift の degraded を PR12 read-only blocker として読む。

現在状態:

- phase gate は `READ_ONLY_GO`。
- `phase2_entry_allowed=true`。
- `P2_BLOCKER=0`。
- `LIVE_READINESS_BLOCKER=6`。
- read-only / P2 entry / paper / live は別 surface。

責任 surface:

- `uv run sis phase-gate-review`
- `src/sis/reports/phase_gate_review.py`
- `data/ops/phase_gate_review_summary.json`
- `docs/OPERATIONS_RUNBOOK.md`

Stop condition:

- `READ_ONLY_GO` ではない。
- `strict_validation_issue_count > 0`。
- `P2_BLOCKER > 0`。
- `LIVE_READINESS_BLOCKER > 0` を live ready と読んでいる。

Recovery / verification:

```bash
uv run sis phase-gate-review
uv run sis bot-preview
```

完了条件:

- P2 entry 判定と live-readiness 判定を別に読める。
- generated summary に drift classification が残っていても、P2 blocker か live blocker かを分類できる。

## 7. Real Market Provider / Source Confidence Failure

State: `ACTIVE_LIVE_READINESS`

壊れ方:

- real-market provider が欠損、遅延、異常値を返す。
- credentials 未設定と provider outage を区別できない。
- offline unit test success を Alpaca live API success と読む。
- low confidence source を live / paper-to-live candidate として扱う。

現在状態:

- Alpaca provider は silent stub ではない。
- credentials 未設定、request failure、non-JSON response、empty bars は `AlpacaProviderUnavailable` で止まる。
- `uv run sis alpaca-smoke` は `pass` / `blocked` / `failed` のどれでも summary / report を残す operator entry。
- live bars が返っても source confidence が低ければ `status=blocked` で止まる。
- credentials ありの live API success は未検証。

責任 surface:

- `src/sis/real_market/providers/alpaca.py`
- `src/sis/real_market/`
- `src/sis/research/`
- `tests/test_alpaca_provider.py`
- `tests/test_real_vs_venue_tracking.py`

Stop condition:

- Alpaca credentials がない。
- live API request が成功していない。
- provider returned no bars。
- source confidence が低い。
- yfinance / fallback source を live truth として扱っている。

Recovery / verification:

```bash
uv run sis alpaca-smoke --symbol NVDA --timeframe 15m --limit 1 --feed iex
uv run pytest tests/test_alpaca_provider.py tests/test_real_vs_venue_tracking.py -q
```

完了条件:

- offline provider behavior が unit test で pass。
- credentials あり環境で Alpaca live smoke が `status=pass`。
- live / paper-to-live 判定で provider type と source confidence が説明できる。

## 8. Tracking Truth / Mid-vs-Mark Failure

State: `RESOLVED_GUARD`

壊れ方:

- `mid_price` を `mark_price` の代用として tracking diff に使う。
- missing mark を diff value で隠す。
- real-market quality failure と venue quote failure を tracking 側で混ぜる。
- tracking divergence を根因確定として扱う。

現在状態:

- `mark_real_diff_bps` は `quote.mark_price` only。
- `quote.mark_price is None` なら `mark_real_diff_bps is None`。
- missing mark は `BLOCK_MISSING_MARK_PRICE` として止まる。
- `mid_price` は venue mid として残るが、mark-real diff には使わない。

責任 surface:

- `src/sis/tracking/real_vs_venue.py`
- `src/sis/tracking/models.py`
- `tests/test_real_vs_venue_tracking.py`
- `tests/test_lead_lag.py`

Stop condition:

- `mark_real_diff_bps` が mid fallback で埋まる。
- missing mark なのに trade allowed になる。
- low source confidence なのに tracking gate を通る。

Recovery / verification:

```bash
uv run pytest tests/test_real_vs_venue_tracking.py tests/test_tracking_models.py tests/test_lead_lag.py -q
```

完了条件:

- missing mark case で `mark_real_diff_bps is None`。
- `BLOCK_MISSING_MARK_PRICE` が出る。
- `trade_allowed=false`。

## 9. Session / Tradability Boundary Failure

State: `RESOLVED_GUARD`

壊れ方:

- venue book があることを underlying market open と読む。
- `market_status`、`session_type`、`is_tradable` の意味を混ぜる。
- closed session を execution candidate として扱う。
- XAU / metals / FX / pure crypto の old calendar surface を active Trade[XYZ] path として読む。

現在状態:

- XNYS calendar docs は underlying session の説明として scoped。
- active Trade[XYZ] target symbols は equity / index basket 側へ寄せている。
- XAU は current active target universe ではない。

責任 surface:

- `src/sis/market_calendar.py`
- `src/sis/risk/halt_policy.py`
- `src/sis/tracking/real_vs_venue.py`
- `docs/XNYS_MARKET_CALENDAR.md`

Stop condition:

- `session_type=UNKNOWN` を live tradable として扱う。
- active CLI smoke / gate が XAU を current target として要求する。
- underlying session 未解決なのに execution candidate へ進む。

Recovery / verification:

```bash
uv run pytest tests/test_market_calendar.py tests/test_real_vs_venue_tracking.py tests/test_halt_policy.py -q
uv run sis next-live-window --venue trade_xyz --symbol SP500
```

完了条件:

- underlying session と venue quote availability を別に説明できる。
- unsupported / inactive symbol が active target universe に戻らない。

## 10. Execution Drift / Live Readiness Failure

State: `ACTIVE_LIVE_READINESS`

壊れ方:

- execution lineage degraded を P2 blocker として誤読する。
- balance / fills / registry comparison / snapshot drift を read-only quote gate の failure として扱う。
- live-readiness blocker が残っているのに live ready とする。
- paper state と execution observation の mismatch を無視する。

現在状態:

- `P2_BLOCKER=0`。
- `LIVE_READINESS_BLOCKER=6`。
- phase gate remediation order は、only live-readiness blockers の場合 `none`。
- current live-readiness blockers:
  - `execution_drift_overview_status`: observed `degraded`, expected `ok`
  - `execution_balance_gap_detected`: observed `true`, expected `false`
  - `execution_fills_gap_detected`: observed `true`, expected `false`
  - `execution_comparison_all_registries_present`: observed `false`, expected `true`
  - `execution_state_comparison_mismatching_count`: observed `3`, expected `0`
  - `execution_snapshot_drift_mismatching_snapshot_count`: observed `3`, expected `0`

責任 surface:

- `src/sis/reports/phase_gate_review.py`
- `src/sis/reports/summary_normalizers.py`
- `data/ops/phase_gate_review_summary.json`
- execution comparison / state / snapshot artifacts under `data/`

Stop condition:

- `execution_drift_classification_counts.LIVE_READINESS_BLOCKER > 0` を live ready と読む。
- execution drift を `P2_BLOCKER` に戻して P2 entry を止める。
- execution comparison artifacts の absence / mismatch を分類せずに degraded とだけ書く。

Recovery / verification:

```bash
uv run sis phase-gate-review
uv run pytest tests/test_phase_gate_review.py tests/test_monitoring_comparison.py -q
```

完了条件:

- P2 判定では `P2_BLOCKER=0` を確認する。
- live-readiness 判定では `LIVE_READINESS_BLOCKER=0` まで解消する。
- P2 remediation order は live-readiness-only drift を再生成ループに入れない。
- drift signal ごとに observed / expected / classification が report で説明できる。

## 11. Legacy / Current Surface Confusion

State: `RESOLVED_GUARD`

壊れ方:

- archived gTrade/Ostium docs を current Trade[XYZ] runbook として読む。
- legacy collector risk を current PR12 blocker として扱う。
- old sidecar command や XAU smoke を active CLI surface として扱う。
- `ostium-python-sdk` など legacy dependency を current dependency として読む。

現在状態:

- current collector surface は `uv run sis collect-trade-xyz-quotes`。
- legacy docs は履歴 / risk review として読む。
- current docs の read-first は `CURRENT_STATE.md`, `CODE_STATUS.md`, `OPERATIONS_RUNBOOK.md`, `ARCHITECTURE_AND_PHASES.md`, `DOCUMENT_AUDIT_2026-05-30.md`。

責任 surface:

- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/DOCUMENT_AUDIT_2026-05-30.md`
- legacy collector docs and archives

Stop condition:

- current task が legacy command を標準手順として要求している。
- current gate を legacy artifact blocker で説明している。
- active docs root で old gTrade/Ostium/XAU path が current path に見える。

Recovery / verification:

```bash
uv run sis --help
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --dry-run
```

完了条件:

- current Trade[XYZ] path と legacy archive path が docs 上で分かれている。
- legacy docs を current operator runbook として読まない。

## 12. Generated Report Staleness Failure

State: `RESOLVED_GUARD`

壊れ方:

- `data/reports/*.md` の old symbol / old decision を current source doc として読む。
- generated report を手編集する。
- operations dashboard、readiness snapshot、current state index が latest gate とずれる。
- stale generated report を根拠に current blocker を再導入する。

現在状態:

- `data/ops/*.json` は generated current snapshot。
- `data/reports/*.md` は generated readable snapshot。
- `data/reports/weekly_strategy_review.md` は current Trade[XYZ] gate snapshot を先頭に出し、old symbols を historical/backtest input と明示する。
- weekly review は `Paper Last Run Phase Gate` と current `phase_gate_review_summary.json` の差分も別セクションで明示する。
- source docs は `docs/`、runtime snapshot は `data/ops/`、generated readable report は `data/reports/` として分ける。

責任 surface:

- `uv run sis implementation-status --write`
- `uv run sis refresh-operations-artifacts`
- `uv run sis phase-gate-review`
- `src/sis/reports/`
- `data/reports/*.md`
- `data/ops/*.json`

Stop condition:

- generated report の timestamp / decision / blocker が latest artifact と合わない。
- generated report を source doc として手編集している。
- old symbol set が current Trade[XYZ] target universe として読まれている。

Recovery / verification:

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

完了条件:

- current docs は source of truth と generated snapshot を分けている。
- generated reports の stale risk が docs audit に反映されている。
- weekly review の `Backtest Metrics Snapshot` を current Trade[XYZ] target universe と誤読しない。
- weekly review の `Paper Last Run Phase Gate` を latest phase gate summary と誤読しない。

## FD Status Mapping

| FD | current status | next done condition |
|---|---|---|
| FD-01 legacy 混入 | `RESOLVED_GUARD` | active docs / CLI / gate が Trade[XYZ] target universe を標準にし、legacy docs は履歴扱い |
| FD-02 identity 誤認 | `RESOLVED_GUARD` | registry / quote / diagnostics の target symbols と fee fields が一致 |
| FD-03 API 部分欠損 | `RESOLVED_GUARD` | Trade[XYZ] summary が endpoint failure を隠さず、strict validation が green |
| FD-04 quote 意味汚染 | `RESOLVED_GUARD` | mark / oracle / funding / OI / fee / depth / stale を diagnostics と gate が見る |
| FD-05 流動性過大評価 | `RESOLVED_GUARD` | side-specific depth と spread p90 を diagnostics / gate で確認 |
| FD-06 fresh 判定 | `RESOLVED_GUARD` | latest refresh と PR12 long-window evidence を混同しない |
| FD-07 real market 品質 | `ACTIVE_LIVE_READINESS` | credentials あり Alpaca live smoke と source confidence policy が green |
| FD-08 session 混同 | `RESOLVED_GUARD` | venue availability と underlying session を別に止める |
| FD-09 tracking 誤陽性 | `RESOLVED_GUARD` | missing mark で mid fallback せず、trade disallowed |
| FD-10 fee / cost | `RESOLVED_GUARD` | fee unknown の再発で gate が落ちる |
| FD-11 artifact chain 混在 | `RESOLVED_GUARD` | strict validation が Trade[XYZ] chain で pass し、legacy-only pass にならない |
| FD-12 paper / live 乖離 | `ACTIVE_LIVE_READINESS` | execution drift classification が `LIVE_READINESS_BLOCKER=0` |
| FD-13 micro live 安全 | `DEFERRED` | public live CLI / signing / cancel-close safety を別計画で確認 |
| FD-14 観測不能 | `RESOLVED_GUARD` | phase gate / diagnostics / docs audit が current blocker classification を出す |

## 実務上の読み方

赤い値を見たら、まず機能名ではなく失敗モードで分類する。

1. stale artifact / provenance か。
2. external source / market window か。
3. venue identity / registry mapping か。
4. quote quality / fee certainty か。
5. schema / strict validation か。
6. gate interpretation か。
7. real market provider / source confidence か。
8. tracking truth / mid-vs-mark か。
9. session / tradability boundary か。
10. execution drift / live readiness か。
11. legacy / current surface confusion か。
12. generated report staleness か。

分類してから、該当する CLI、artifact、test へ戻る。

## この文書と既存 docs の関係

- `docs/CURRENT_STATE.md`: restart 時の短い current truth。
- `docs/CODE_STATUS.md`: code surface と implementation status。
- `docs/OPERATIONS_RUNBOOK.md`: 再生成と運用手順。
- `docs/ARCHITECTURE_AND_PHASES.md`: subsystem / phase の入口。
- `docs/DOCUMENT_AUDIT_2026-05-30.md`: docs lifecycle と stale-risk の入口。
- この文書: 壊れ方を基準に、責任境界、stop condition、完了条件を読むための current map。
