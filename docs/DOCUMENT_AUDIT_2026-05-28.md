# Documentation Audit 2026-05-28

コード、設定、tests、CLI help、runtime artifact を正として、tracked docs と generated reports を再監査した結果。

## 結論

current docs の正本は次の 7 本に寄せる。

1. `docs/CURRENT_STATE.md`
2. `docs/CODE_STATUS.md`
3. `docs/OPERATIONS_RUNBOOK.md`
4. `docs/ARCHITECTURE_AND_PHASES.md`
5. `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md`
6. `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md`
7. `docs/DOCUMENT_AUDIT_2026-05-28.md`

`docs/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md` は「実装済み計画 + 実装結果」として残す。今後の実行 plan としては読まない。

2026-05-28 の current truth:

```text
./scripts/check:
  288 passed

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

重要な読み替え:

- `fee_mode_unknown_rate=1.0` は current blocker ではない。再発した場合の regression signal として読む。
- `READ_ONLY_GO` は production live trading ready ではない。
- execution drift は current P2 blocker ではなく live-readiness blocker として残る。
- Alpaca provider は silent stub ではない。ただし credentials ありの live API success は未検証。

## 今回修正した docs

| file | 修正内容 |
|---|---|
| `README.md` | 2026-05-28 の gate / strict validation / test count / fee mode / Alpaca provider 境界へ更新 |
| `docs/CURRENT_STATE.md` | `fee_mode_unknown_rate=1.0` を current fact から削除し、fee resolution / Alpaca / execution drift classification を反映 |
| `docs/CODE_STATUS.md` | P2 gate restore、execution drift classification、Alpaca provider stub removal を current status に追加 |
| `docs/OPERATIONS_RUNBOOK.md` | Trade[XYZ] refresh path、fee propagation、Alpaca credentials、current artifact / PR12 long-window evidence の境界を明確化 |
| `docs/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md` | 実装済み計画であること、pre-implementation snapshot であることを明記 |
| `docs/DOCUMENT_AUDIT_2026-05-27.md` | superseded banner を追加 |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` | superseded banner を追加 |

## Lifecycle Classification

### Current / Read First

| file | status | 理由 | 完了条件 |
|---|---|---|---|
| `README.md` | current | 最短入口。CLI、gate、boundary を最新化済み | `./scripts/check`, `validate-artifacts --strict`, `phase-gate-review` の値と矛盾しない |
| `docs/CURRENT_STATE.md` | current | repo restart 時の短い current truth | current artifact の phase gate / strict validation / blocker 分類を反映している |
| `docs/CODE_STATUS.md` | current | code surface と tests の実装状態 | PR/P2 status と tests が一致する |
| `docs/OPERATIONS_RUNBOOK.md` | current | operator が再生成するための手順 | current CLI に存在しない command を標準手順として出さない |
| `docs/ARCHITECTURE_AND_PHASES.md` | current, minor risk | 大枠は code truth と一致。詳細数値は持たない | legacy / Trade[XYZ] / micro live boundary が崩れていない |
| `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md` | current | 壊れ方単位の責任境界。P2 blocker と live-readiness blocker を分離済み | `READ_ONLY_GO`, `P2_BLOCKER=0`, `LIVE_READINESS_BLOCKER=6` を current truth として扱う |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` | current | Trade[XYZ] 実装状況の current audit。P2 gate restore 後の値へ更新済み | `checked_files=12`, `288 passed`, fee mode resolved, Alpaca non-stub を current truth として扱う |
| `docs/XNYS_MARKET_CALENDAR.md` | current, scoped | underlying session の説明として有効 | active XAU surface と混同しない |

### Current But Historical-Result Oriented

| file | status | 理由 | 完了条件 |
|---|---|---|---|
| `docs/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md` | implemented-plan | P2-00〜P2-05 の作業記録として有用。冒頭に current status を追加済み | 今後の未実装 plan と誤読されない |
| `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-27.md` | historical design reference | 壊れ方単位の判断軸として有用。ただし一部の例は実装前 state。2026-05-28 版へ superseded 済み | current fact ではなく historical failure-mode design として読む |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` | historical audit | P2 gate restore 前の棚卸し。2026-05-28 版へ superseded 済み | current status として引用しない |
| `docs/DOCUMENT_AUDIT_2026-05-27.md` | historical audit | PR12 時点の docs audit。superseded 表示済み | current audit は本ファイルを読む |
| `docs/DOCUMENT_AUDIT_2026-05-26.md` | old snapshot | すでに superseded 表示あり | archive へ移すか、snapshot としてだけ残す |

### Legacy / Archive-Oriented

| file | status | 理由 | 完了条件 |
|---|---|---|---|
| `docs/archive/legacy_read_only_collectors_2026-05-28/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md` | archived legacy reference | gTrade/Ostium collector chain の履歴 | current Trade[XYZ] CLI と混同しない |
| `docs/archive/legacy_read_only_collectors_2026-05-28/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md` | archived legacy consumed/partial plan | gTrade/Ostium path の未実装 backlog を含む。current public CLI ではない | future legacy restore 時だけ参照する |
| `docs/archive/legacy_read_only_collectors_2026-05-28/READ_ONLY_COLLECTOR_RISK_REVIEW.md` | archived legacy risk review | old collector risk として有用。current gate の blocker ではない | future legacy restore 時だけ参照する |
| `docs/live_evidence_reports/README.md` | generated-history index | live evidence report は history / generated artifact | current status として読まない |
| `docs/archive/**` | archive | historical only | current runbook から command を拾わない |

### Generated / Runtime Snapshot

| path | status | 扱い |
|---|---|---|
| `data/ops/*.json` | generated current snapshot | code truth の次に見る。古ければ再生成 |
| `data/reports/*.md` | generated current snapshot |手編集しない。`uv run sis refresh-operations-artifacts` 等で再生成 |
| `data/reports/phase_gate_review.md` | generated gate report | current gate 説明として有用だが、sourceは `src/sis/reports/phase_gate_review.py` |
| `data/reports/quote_diagnostics.md` | generated diagnostics | latest Trade[XYZ] quote file 評価に寄せている |
| `data/reports/weekly_strategy_review.md` | generated, stale-risk | QQQ/SPY/XAU など old symbols が出る場合がある。current Trade[XYZ] status docs ではない |

## 古い内容がある docs

| file | stale content | 修正方針 |
|---|---|---|
| `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-27.md` | `fee_mode_unknown_rate=1.0` を未解決例として扱う箇所 | 設計資料として残す。必要なら `2026-05-28 resolved` 注記を追加 |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` | fee mode unknown、Alpaca stub、2026-05-27 artifact 値 | superseded 済み。全面更新より archive 扱いが安全 |
| `docs/DOCUMENT_AUDIT_2026-05-27.md` | `280 passed`, `checked_files=11`, 2026-05-27 PR12 値 | superseded 済み |
| `docs/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md` | 冒頭の pre-implementation `NO_GO` / fee unknown snapshot | implemented-plan として注記済み。pre snapshot は履歴として残す |
| `docs/READ_ONLY_COLLECTOR_*` | gTrade/Ostium command / XAU / legacy endpoint | legacy 表示があるので current docs としては使わない |

## 作り直したほうがいい docs

### 1. `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md`

作り直し済み:

```text
docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md
```

理由:

- 2026-05-27 audit は長く、P2 gate restore 前の事実が多い。
- 部分修正すると「当時の証跡」と「現在の status」が混ざる。
- current audit として作り直すなら、PR9a-PR12 + P2-00〜P2-05 の結果だけに絞るほうがよい。

完了条件:

- `fee_mode_unknown_rate=1.0` を current blocker として書かない。
- `Alpaca provider is stub` と書かない。
- `checked_files=12`, `288 passed`, `READ_ONLY_GO`, `P2_BLOCKER=0`, `LIVE_READINESS_BLOCKER=6` を反映する。
- production live trading ready ではないことを明記する。

現在状態:

- `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` に反映済み。

### 2. `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-27.md`

作り直し済み:

```text
docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md
```

理由:

- failure-mode の軸は有用。
- ただし FD ごとの state は P2 実装後に変わった。
- current blocker は fee unknown ではなく live-readiness drift と Alpaca live credentials smoke。

完了条件:

- resolved / active / deferred を FD ごとに分ける。
- `fee_mode_unknown_rate` は regression check へ移す。
- `execution_drift_classifications` を live-readiness failure mode として入れる。

現在状態:

- `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md` に反映済み。

### 3. Legacy read-only collector docs 3 本

対象:

- `docs/archive/legacy_read_only_collectors_2026-05-28/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md`
- `docs/archive/legacy_read_only_collectors_2026-05-28/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md`
- `docs/archive/legacy_read_only_collectors_2026-05-28/READ_ONLY_COLLECTOR_RISK_REVIEW.md`

現在状態:

- `docs/archive/legacy_read_only_collectors_2026-05-28/` に archive 済み。
- current runbook は archive directory を指す。

完了条件:

- active docs search で `uv run sis ostium-constraint-artifact` や `bun run gtrade:*` が current command に見えない。
- current Trade[XYZ] path は `collect-trade-xyz-quotes` に一本化されている。

## 削除・アーカイブしてよい候補

削除より archive move を推奨する。理由は、過去の判断根拠としてはまだ使えるため。

| candidate | 推奨 | 理由 |
|---|---|---|
| `docs/DOCUMENT_AUDIT_2026-05-26.md` | archive | 2026-05-27 / 2026-05-28 audit に superseded |
| `docs/DOCUMENT_AUDIT_2026-05-27.md` | archive later | 本ファイルに superseded。すぐ削除せず履歴として残す |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` | archive after 2026-05-28 rewrite | P2 前の棚卸しとしては有用 |
| `docs/archive/legacy_read_only_collectors_2026-05-28/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md` | archived | legacy gTrade/Ostium plan |
| `docs/archive/legacy_read_only_collectors_2026-05-28/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md` | archived | legacy gTrade/Ostium collector docs |
| `docs/archive/legacy_read_only_collectors_2026-05-28/READ_ONLY_COLLECTOR_RISK_REVIEW.md` | archived | legacy risk review |
| `docs/live_evidence_reports/*` | archive/generated history | current source docs ではない |

## 抜け・漏れ・誤謬リスク

### R1. `READ_ONLY_GO` の誤読

Risk:

`phase2_entry_allowed=true` を live trading ready と読む。

Current guard:

- `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md`, `docs/OPERATIONS_RUNBOOK.md` に live-readiness blocker を明記。
- `phase_gate_review_summary.json` に `P2_BLOCKER=0`, `LIVE_READINESS_BLOCKER=6` がある。

Current guard:

- `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md` で live-readiness blocker を failure mode として正本化済み。

### R2. PR12 long-window artifact と latest quote artifact の混同

Risk:

`trade_xyz_quote_collection_summary.json` は latest refresh で上書きされるため、PR12 の 310 rows と current latest 11 rows を混同する。

Current guard:

- runbook に current artifact と PR12 long-window evidence を分離して記載。

Better:

- long-window smoke summary は `pr12_fresh_read_only_smoke_summary.json` を正本にし、latest collection summary を PR12 evidence と呼ばない。

### R3. Alpaca provider の検証過大評価

Risk:

offline unit test が通ったことを、実 Alpaca API live success と読む。

Current guard:

- docs に credentials あり live API success は未検証と明記。

Better:

- credentials がある環境だけで `tests/test_alpaca_provider_live.py` または `uv run sis alpaca-smoke` 相当を追加する。

### R4. Legacy docs の current command 誤認

Risk:

`gtrade` / `ostium` / `XAU` を active implementation surface と読む。

Current guard:

- legacy docs の冒頭 banner は存在。
- runbook は Trade[XYZ] refresh path を標準化。
- legacy docs 3 本は `docs/archive/legacy_read_only_collectors_2026-05-28/` へ移動済み。

Better:

- archive README を current docs からの唯一の入口として維持する。

### R5. Generated reports の stale 値

Risk:

`data/reports/*.md` は regenerated snapshot であり、old symbol や old decision が混ざる場合がある。

Current guard:

- source docs では generated と明記。

Better:

- docs audit では generated reports を lifecycle table に分け、手編集しない rule を維持する。

## Next Better Work

優先順:

1. Alpaca live credentials smoke の operator doc を追加する。ただし secrets は repo に書かない。
2. `data/reports/weekly_strategy_review.md` が old symbol を出す理由を調べ、generated report の current symbol universe と legacy history を分ける。

完了済み:

- `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md` を新規作成し、FD state を resolved / active / deferred に更新した。
- `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` を新規作成し、2026-05-27 audit を current status から外した。
- legacy read-only collector docs 3 本を `docs/archive/legacy_read_only_collectors_2026-05-28/` へ移動した。

## Verification

この audit 作成時に確認したコマンド:

```bash
uv run sis --help
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
./scripts/check
```

確認結果:

```text
uv run sis --help: pass
uv run sis validate-artifacts --strict: checked_files=12, issues=0
uv run sis phase-gate-review: READ_ONLY_GO, phase2_entry_allowed=true, blockers=[]
./scripts/check: pass, 288 passed
```
