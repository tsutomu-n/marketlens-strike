# Failure Mode Responsibility Map 2026-05-27

この文書は `marketlens-strike` を機能単位ではなく、壊れ方単位で読むための整理メモです。

## 結論

本当に混在を消すなら、責任境界は `collector`、`validator`、`report`、`gate`、`execution` では切らない。

この repo で混ざりやすいのは、機能ではなく次の壊れ方です。

- 古い artifact を現在の判断材料として読んでしまう
- read-only gate の成功を live trading readiness と読んでしまう
- 外部 API failure、market closed、schema failure、quote quality failure を同じ `missing artifact` に潰してしまう
- legacy gTrade/Ostium と current Trade[XYZ] を同じ evidence chain として読んでしまう
- paper / tracking / execution drift の degraded を PR12 read-only gate の blocker として誤読する

したがって、責任は「どの機能が処理したか」ではなく「どの壊れ方を止めるか」で分ける。

## 1. Artifact Freshness / Provenance Failure

壊れ方:

- `data/` 配下の generated artifact が古い
- summary は新しく見えるが raw file、parquet、DuckDB、report が別 run のもの
- append / rerun / manual copy により、latest と final がずれる
- `phase_gate_review_summary.json` だけを見て、元 artifact の鮮度を見ない

混ぜてはいけないもの:

- artifact の存在確認
- artifact の鮮度確認
- artifact 間の同一 run 確認
- gate decision の意味解釈

責任を持つコード/CLI/artifact:

- `uv run sis collect-trade-xyz-quotes --write-summary --write-report`
- `uv run sis validate-artifacts --strict`
- `uv run sis phase-gate-review`
- `data/ops/trade_xyz_quote_collection_summary.json`
- `data/ops/phase_gate_review_summary.json`
- `data/reports/phase_gate_review.md`

止める条件:

- generated artifact が欠けている
- checked file count が想定より少ない
- summary と raw evidence の row count / window / symbol set が説明できない
- `next_actions` が空でない

復旧確認:

```bash
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

まだ混在しやすい注意点:

- `READ_ONLY_GO` は artifact chain がその時点で閉じたという意味であり、古い artifact を再利用してよいという意味ではない。
- `data/` は git 管理外なので、再開時は current file の中身を見ずに docs だけで判断しない。

## 2. External Source / Market Window Failure

壊れ方:

- venue API が落ちる、遅い、空 payload を返す
- XNYS / shared market window が閉じていて十分な観測 window が取れない
- 60-minute smoke のつもりが短い window で終わる
- provider の一時失敗を schema failure や implementation failure と誤診する

混ぜてはいけないもの:

- market closed
- external provider outage
- local parser bug
- insufficient observation window

責任を持つコード/CLI/artifact:

- `uv run sis probe trade-xyz`
- `uv run sis collect-trade-xyz-quotes --duration-minutes ... --interval-seconds ...`
- `src/sis/market_calendar.py`
- `src/sis/venues/trade_xyz/client.py`
- `src/sis/venues/trade_xyz/collector.py`
- `data/ops/pr12_fresh_read_only_smoke_summary.json`

止める条件:

- `observed_window_seconds < 3600` for PR12 smoke
- row count が target symbol x expected intervals に届かない
- fetch failure が raw error / summary に残っていない
- market closed と API failure の区別が artifact に残っていない

復旧確認:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --symbols SP500,XYZ100,NVDA,AAPL,MSFT --duration-minutes 60 --interval-seconds 60 --normalize --replace --write-summary --write-report
```

まだ混在しやすい注意点:

- closed market は code regression ではない。
- provider failure を fallback で隠すと、read-only evidence の意味が薄くなる。

## 3. Venue Identity / Registry Mapping Failure

壊れ方:

- Trade[XYZ] symbol と HIP-3 `asset_id` がずれる
- `perpDexs` 由来の mapping と legacy-looking fallback を同じ信頼度で読む
- `api_orderable=false` の銘柄を execution candidate として扱う
- registry が古いまま quote collection に使われる

混ぜてはいけないもの:

- symbol name resolution
- `asset_id` resolution
- orderability
- fallback provenance

責任を持つコード/CLI/artifact:

- `uv run sis probe trade-xyz`
- `src/sis/venues/trade_xyz/registry.py`
- `src/sis/venues/trade_xyz/models.py`
- `data/registry/trade_xyz_instruments.json`

止める条件:

- `asset_id` が未解決
- mapping source が説明できない
- `api_orderable=false`
- registry と quote summary の symbol universe が一致しない

復旧確認:

```bash
uv run sis probe trade-xyz
uv run pytest tests/test_trade_xyz_registry.py -q
```

まだ混在しやすい注意点:

- fallback は fail-closed の補助であり、execution readiness の根拠ではない。
- registry が正しくても、quote quality や fee mode が正しいとは限らない。

## 4. Quote Quality Failure

壊れ方:

- mark price / index price / oracle timestamp が欠ける
- stale quote が混ざる
- spread、depth、funding、fee mode が execution 判断に足りない
- `depth_10bps_usd` の合算を side-specific depth と誤読する
- `fee_mode_unknown_rate=1.0` を read-only では警告、micro live では blocker と切り替えられない

混ぜてはいけないもの:

- quote が取得できたこと
- quote が新鮮であること
- paper に使えること
- micro live に使えること

責任を持つコード/CLI/artifact:

- `uv run sis diagnose-quotes --venue trade_xyz`
- `src/sis/venues/trade_xyz/normalizer.py`
- `src/sis/venues/trade_xyz/quality.py`
- `src/sis/reports/quote_diagnostics.py`
- `data/reports/trade_xyz_quote_diagnostics.md`

止める条件:

- stale rate が policy threshold を超える
- missing mark / index / oracle timestamp が多い
- side-specific depth が必要な場面で合算 depth しかない
- fee mode が unknown のまま micro live 候補へ進む

復旧確認:

```bash
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
```

まだ混在しやすい注意点:

- PR12 read-only gate は quote collection と validation の gate であり、micro live fee certainty の gate ではない。
- paper gate と live order gate は同じ quote artifact を読んでも、止める基準が違う。

## 5. Schema / Strict Validation Failure

壊れ方:

- required field が欠ける
- schema は通るが semantic contract が弱い
- checked files が少ないのに pass と読まれる
- raw / normalized / summary / report の contract が片方だけ更新される

混ぜてはいけないもの:

- JSON schema validation
- semantic quality validation
- artifact existence
- gate decision

責任を持つコード/CLI/artifact:

- `uv run sis validate-artifacts --strict`
- `src/sis/validation/artifacts.py`
- `schemas/quote_log_v2.schema.json`
- `schemas/trade_xyz_quote_collection_summary.schema.json`

止める条件:

- `issues > 0`
- `checked_files < 1`
- strict validation issue preview が残る
- schema change と artifact writer change が同期していない

復旧確認:

```bash
uv run sis validate-artifacts --strict
uv run pytest tests/test_validate_artifacts_trade_xyz.py -q
```

まだ混在しやすい注意点:

- strict validation が green でも、execution readiness は別判定。
- schema validation は provider outage の根因説明ではない。

## 6. Gate Interpretation Failure

壊れ方:

- `READ_ONLY_GO` を production live ready と読む
- `phase2_entry_allowed=true` を micro live allowed と読む
- `CONDITIONAL_INDEX_ONLY` や `NO_GO` の blocker を機能別に追い、壊れ方を見失う
- `next_actions=[]` の意味を「すべて完了」と読む

混ぜてはいけないもの:

- read-only PR12 gate
- Phase 2 entry
- paper readiness
- micro live readiness
- production live readiness

責任を持つコード/CLI/artifact:

- `uv run sis phase-gate-review`
- `src/sis/reports/phase_gate_review.py`
- `data/ops/phase_gate_review_summary.json`
- `docs/OPERATIONS_RUNBOOK.md`

止める条件:

- decision が `READ_ONLY_GO` ではない
- `next_actions` が空でない
- strict validation issue が残る
- live execution readiness と同じ意味で読まれている

復旧確認:

```bash
uv run sis phase-gate-review
uv run sis bot-preview
```

まだ混在しやすい注意点:

- `bot-preview` は read-only の HOLD decision / preview artifact であり、注文発注 surface ではない。
- `phase-gate-review` は Bot 前の現行判定正本だが、wallet / signing / exchange write API を証明しない。

## 7. Research Truth Failure

壊れ方:

- real-market provider が欠損、遅延、異常値を返す
- event calendar が古い
- feature panel が欠損している
- source confidence が低いのに trading candidate として扱う

混ぜてはいけないもの:

- venue quote truth
- real-market price truth
- research feature truth
- event blackout truth

責任を持つコード/CLI/artifact:

- `uv run sis ingest-research-data`
- `uv run sis build-event-calendar`
- `uv run sis build-feature-panel`
- `uv run sis check-research-quality`
- `src/sis/real_market/`
- `src/sis/research/`

止める条件:

- source confidence が低い
- feature panel が古い
- event blackout の判定材料が欠ける
- provider fallback の provenance が説明できない

復旧確認:

```bash
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis check-research-quality
```

まだ混在しやすい注意点:

- venue quote が正常でも、research truth が壊れていれば strategy / paper / live candidate は止める。
- research data の fallback は便利だが、primary と fallback を同じ信頼度で混ぜない。

## 8. Tracking Divergence Failure

壊れ方:

- real-market と venue quote の差分が大きい
- lead/lag が崩れる
- tracking gate が degradation を検出しているのに paper fill へ進む
- divergence の理由を quote quality failure と混同する

混ぜてはいけないもの:

- quote quality
- real-market quality
- real vs venue divergence
- trade-allowed decision

責任を持つコード/CLI/artifact:

- `src/sis/tracking/`
- `tests/test_real_vs_venue_tracking.py`
- `tests/test_lead_lag.py`
- tracking reports under `data/reports/`

止める条件:

- tracking decision が trade allowed ではない
- divergence が threshold を超える
- source confidence と venue quality の両方が揃っていない

復旧確認:

```bash
uv run pytest tests/test_tracking_models.py tests/test_real_vs_venue_tracking.py tests/test_lead_lag.py -q
```

まだ混在しやすい注意点:

- tracking は「どちらが壊れたか」を確定する場所ではなく、「差分が大きいので進めない」を出す場所。
- 根因は quote、research、calendar、provider のどれかへ戻して切る。

## 9. Paper Simulation Failure

壊れ方:

- fill price が best bid / ask ではない
- cost model が fee mode / spread / funding を誤って読む
- portfolio state と report がずれる
- paper success を live execution success と読む

混ぜてはいけないもの:

- paper execution
- read-only execution observation
- micro live safety canary
- production live execution

責任を持つコード/CLI/artifact:

- `uv run sis paper-operations-cycle`
- `src/sis/paper/`
- `src/sis/core/execution_plan.py`
- `configs/fee_model.trade_xyz.yaml`
- `data/reports/daily_paper_report.md`

止める条件:

- venue quality / tracking gate が trade allowed ではない
- fee mode が unknown のまま cost を確定扱いしている
- fill / position / report の state が一致しない

復旧確認:

```bash
uv run sis paper-operations-cycle
uv run pytest tests/test_paper_trading.py tests/test_paper_runner.py -q
```

まだ混在しやすい注意点:

- paper は safety rehearsal であり、wallet / signing / write API の証明ではない。
- paper report が green でも micro live public CLI は別境界。

## 10. Execution Safety Failure

壊れ方:

- micro live safety code があることを live trading ready と読む
- signing / wallet / exchange secrets が未接続なのに注文可能と扱う
- public CLI が未公開なのに operator path があると読まれる
- cancel / close / reduce-only safety の失敗を paper の問題として扱う

混ぜてはいけないもの:

- execution read-only observation
- micro live safety canary
- public operator CLI
- production live trading

責任を持つコード/CLI/artifact:

- `src/sis/execution/trade_xyz_adapter.py`
- `src/sis/execution/live_order_policy.py`
- `src/sis/execution/micro_live_canary.py`
- `tests/test_trade_xyz_live_order_policy.py`
- `tests/test_trade_xyz_adapter_safety.py`
- `tests/test_micro_live_canary.py`

止める条件:

- signing / wallet / exchange write integration が未レビュー
- public CLI surface が未公開
- market order、notional、leverage、session、event blackout、open-position gate の safety check が通らない
- cancel / close path を確認できない

復旧確認:

```bash
uv run pytest tests/test_trade_xyz_live_order_policy.py tests/test_trade_xyz_adapter_safety.py tests/test_micro_live_canary.py -q
```

まだ混在しやすい注意点:

- 現 repo の標準運用は read-only / paper まで。manual live smoke は標準手順に含めない。
- `READ_ONLY_GO` は exchange write readiness ではない。

## 11. Ops / Restart / Report Drift Failure

壊れ方:

- operations dashboard、readiness snapshot、current state index が古い
- remediation chain が古い blocker を引きずる
- daemon / scheduler の状態を latest gate と混ぜる
- degraded execution lineage を PR12 read-only failure と誤読する

混ぜてはいけないもの:

- current runtime artifact
- restart summary
- operations dashboard
- remediation recommendation
- phase gate decision

責任を持つコード/CLI/artifact:

- `uv run sis implementation-status --write`
- `uv run sis refresh-operations-artifacts`
- `src/sis/reports/`
- `src/sis/ops/`
- `src/sis/state/`
- `data/reports/current_state_index.md`
- `data/reports/readiness_snapshot.md`
- `data/reports/operations_dashboard.md`

止める条件:

- generated summary の timestamp / decision / blocker が latest artifact と合わない
- restart doc が current code/test truth とずれる
- degraded execution status を read-only PR12 blocker として扱っている

復旧確認:

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

まだ混在しやすい注意点:

- operations chain は restart の読みやすさを作る層であり、根の evidence そのものではない。
- degraded は「何が degraded か」を失敗モードに戻して読む。

## 12. Legacy / Current Surface Confusion

壊れ方:

- archived gTrade/Ostium docs を current Trade[XYZ] runbook として読む
- legacy collector risk を current PR12 blocker として扱う
- old sidecar command が active CLI にある前提で手順を書く
- `ostium-python-sdk` が active dependency にあると誤認する

混ぜてはいけないもの:

- current Trade[XYZ] path
- legacy gTrade/Ostium archive
- historical migration plan
- active operator runbook

責任を持つコード/CLI/artifact:

- `docs/CURRENT_STATE.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md`
- `docs/READ_ONLY_COLLECTOR_RISK_REVIEW.md`
- `archive/gtrade_ostium_legacy_archive_*.zip`

止める条件:

- current task が legacy command を要求している
- current gate を legacy artifact blocker で説明している
- active dependency から削除済みの SDK を前提にしている

復旧確認:

```bash
uv run sis --help
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --dry-run
```

まだ混在しやすい注意点:

- legacy docs は履歴とリスクレビューとして読む。
- current collector surface は `uv run sis collect-trade-xyz-quotes`。

## 機能単位から失敗モード単位への読み替え

| 機能名 | 機能としての責任 | 失敗モードとして読む責任 |
|---|---|---|
| `collect-trade-xyz-quotes` | quote collection / normalization / summary | external source failure, market window failure, artifact freshness failure |
| `validate-artifacts --strict` | schema and artifact validation | schema failure, missing file failure, partial writer failure |
| `diagnose-quotes` | quote diagnostics | quote quality failure, fee/depth/staleness blocker separation |
| `phase-gate-review` | operational gate report | gate interpretation failure, strict validation failure, stale artifact exposure |
| `bot-preview` | read-only HOLD / preview artifact | live readiness confusion prevention |
| `paper-operations-cycle` | paper fill and report | paper simulation failure, tracking/venue quality gate misuse |
| `micro_live_canary` code path | tiny live safety sequence | execution safety failure, public CLI / signing boundary |
| `refresh-operations-artifacts` | restart/report aggregation | ops drift failure, stale summary propagation |
| legacy collector docs | historical evidence chain | legacy/current surface confusion |

## 実務上の読み方

何かが赤い時は、まず機能名で追わない。

1. それは stale artifact か。
2. それは external source / market window か。
3. それは registry identity か。
4. それは quote quality か。
5. それは schema / strict validation か。
6. それは gate interpretation か。
7. それは research truth か。
8. それは tracking divergence か。
9. それは paper simulation か。
10. それは execution safety か。
11. それは ops/report drift か。
12. それは legacy/current confusion か。

分類してから、該当する CLI / artifact / test へ戻る。

## この文書と既存 docs の関係

- `docs/CURRENT_STATE.md`: 現在状態の入口。
- `docs/ARCHITECTURE_AND_PHASES.md`: subsystem / phase の入口。
- `docs/OPERATIONS_RUNBOOK.md`: 再生成と運用手順。
- `docs/CODE_STATUS.md`: PR / implementation status の入口。
- この文書: 壊れ方を基準に、責任境界と止める条件を読むための整理図。

