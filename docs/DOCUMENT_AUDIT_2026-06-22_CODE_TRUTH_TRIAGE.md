<!--
作成日: 2026-06-22_14:29 JST
更新日: 2026-06-22_14:55 JST
-->

# Document Audit 2026-06-22 Code Truth Triage

## 結論

コード、テスト、schema、config、CLI help を正にすると、current docs は大きく壊れていない。`scripts/check_current_docs.py` と CLI catalog は通っている。

2026-06-22_14:47 JST に、主な整理対象のうち archive 移動と current-doc checker 対象整理を実行済み。

実行済み:

1. 実装済みになった Crypto Perp MVP plan package を archive へ移動。
2. Strategy Operations Workbench completion plan / audit と旧 2026-06-17 docs audit を archive へ移動。
3. README / CURRENT_STATE / NEXT_DIRECTION / plan README の導線を、現行 runbook / implemented surfaces / historical archive へ更新。
4. assessment docs と `docs/references/crypto_perp/` を current-doc checker 対象へ追加。

残る判断対象:

- `.tmp/live_evidence_*` の tracked helper を今後も残すか、別の archive / scripts へ移すか。

## 確認した正本

- `git status --short --branch`
- `uv run sis --help`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `src/sis/cli.py`
- `src/sis/commands/crypto_perp*.py`
- `src/sis/commands/strategy_daily_brief.py`
- `src/sis/commands/strategy_workbench_viewer.py`
- `src/sis/crypto_perp/`
- `tests/crypto_perp/`
- `schemas/crypto_perp_*.schema.json`
- `docs/CURRENT_STATE.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/strategy_daily_brief/README.md`
- `docs/strategy_workbench_viewer/README.md`
- `plan/README.md`

## 実行結果

```text
git status --short --branch
=> ## main...origin/main

uv run python scripts/check_current_docs.py
=> checked 153 current docs: metadata, links, EOF, legacy roots, HTML sources, semantic drift, and plan routing ok

uv run python scripts/check_cli_catalog.py
=> checked 205 public CLI commands against Typer registration

./scripts/check
=> passed; pytest 1484 passed in 66.69s
```

tracked doc / plan の粗い数:

```text
docs/plan/README/AGENTS related tracked Markdown/HTML files: 611
docs/plan tracked Markdown/YAML/JSON/HTML outside docs/archive and plan/archive: 298
archive ではないが current-doc checker 対象外の Markdown/HTML: 0 after this cleanup
```

archive ではないが current-doc checker 対象外だったため、今回 current-doc checker 対象に追加:

```text
docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md
docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md
docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md
docs/references/crypto_perp/COMPETITION_PROTOCOL.md
docs/references/crypto_perp/HUMMINGBOT_BITGET_CONNECTOR_NOTES.md
docs/references/crypto_perp/OSS_ADOPTION_DECISIONS.md
```

tracked `.tmp`:

```text
.tmp/live_evidence_20260526_2245_cron_once.sh
.tmp/live_evidence_20260526_2245_guard.sh
.tmp/live_evidence_20260526_2245_status.sh
.tmp/live_evidence_20260527_cron_cleanup.sh
.tmp/live_evidence_20260527_recovery_watchdog.sh
.tmp/live_evidence_current_status_2026-05-26.md
```

## 更新できるドキュメント

| 対象 | 判断 | 理由 | 次の作業 |
|---|---|---|---|
| `docs/CURRENT_STATE.md` | 更新 | Crypto Perp の導線がまだ `current implementation handoff` 寄り。コード上は M00-M11 実装済みで、日常運用は runbook / CLI / artifact を読む段階 | plan package を archive に寄せる場合、文言を `implemented plan / historical implementation contract` に変える |
| `README.md` | 更新 | Read First に assessment docs が入っているが、正本ではなく checker 対象外。Crypto Perp plan も実装済み扱いへ変えたい | assessment を残すなら `判断補助` として別枠化。Crypto Perp は runbook / implemented surfaces を上位へ |
| `plan/README.md` | 更新 | `Current 2026-06-20 Crypto Perp Truth-Cycle MVP Plan` が実装済み後も current implementation handoff として残る | `Historical implemented Crypto Perp MVP plan` に変え、archive 移動先を案内 |
| `scripts/check_current_docs.py` | 更新 | current-doc checker は plan package を routing allow しているが、plan package 本文は current docs として lint しない | plan archive 後に allowed prefix を archive 側へ変更し、root plan の再混入を止める |
| `docs/IMPLEMENTED_SURFACES.md` | 小更新候補 | 大筋は合っている。`crypto-perp-tiny-live-measurement` の mock/guarded CLI surface と実ネットワーク未実行の境界をもう少し明示してもよい | current wording を薄く補うだけでよい |
| `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` | 小更新候補 | Crypto Perp artifact/schema の説明は概ね現行。ただし `crypto_perp_live_measurement.v1` を「実ネットワーク測定済みの証明」と誤読しない補強余地あり | `mock artifact もあり、実測済みかは payload と approval/reconciliation を読む` と追記 |
| `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` | 維持更新 | `scripts/check_cli_catalog.py` で 205 command と照合済み。Crypto Perp CLI 群も登録済み | command 追加時だけ更新 |

## アーカイブしたほうがいいドキュメント

| 対象 | 判断 | 理由 | 推奨移動先 |
|---|---|---|---|
| `plan/archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/` | archive 済み | M00-M11 は実装済み。今は実装開始用 handoff ではなく、実装履歴と acceptance 証跡 | `plan/archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/` |
| `docs/archive/2026-06-22-doc-routing/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_PLAN_2026-06-19.md` | archive 済み | completion plan は first slice 実装前/実装中の契約。現行利用者は `IMPLEMENTED_SURFACES.md` と各 domain README を読む方が安全 | `docs/archive/2026-06-22-doc-routing/` |
| `docs/archive/2026-06-22-doc-routing/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_AUDIT_2026-06-19.md` | archive 済み | 監査記録として有用だが固定 pytest 件数 `1340 passed` を含む historical completion audit。current proof ではない | `docs/archive/2026-06-22-doc-routing/` |
| `docs/archive/2026-06-22-doc-routing/DOCUMENT_AUDIT_2026-06-17_CODE_TRUTH_CHECKLIST.md` | archive 済み | 今回の 2026-06-22 audit で置き換えたため旧 audit は historical checklist | `docs/archive/2026-06-22-doc-routing/` |

## 維持するが整理したほうがいいドキュメント

| 対象 | 判断 | 理由 | 次の作業 |
|---|---|---|---|
| `docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md` | current-doc checker 対象化済み | README / CURRENT_STATE から読まれる判断補助。正本ではないため README では Judgment Notes へ下げた | 固定値は当時値として読む。current proof にはしない |
| `docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md` | current-doc checker 対象化済み | 利益目線メモとして有用。正本ではないため README では Judgment Notes へ下げた | 固定値は当時値として読む。current proof にはしない |
| `docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md` | current-doc checker 対象化済み | target definition として参照価値はあるが、current implementation proof ではない | completion plan link は archive 先へ更新済み |
| `docs/references/crypto_perp/` | current-doc checker 対象化済み | Crypto Perp M07 の reference notes。外部ページ参照は drift しうるが、MVP 実装判断の証跡として有用 | `docs/references/crypto_perp/README.md` を追加済み |
| `.tmp/live_evidence_*.sh` / `.tmp/live_evidence_current_status_2026-05-26.md` | 整理 | `.gitignore` では意図的 tracked 扱いだが、日付固定の one-off helper / historical status。現行 operator entry ではない | 必要なら `scripts/` へ汎用化。不要なら archive docs へ記録して tracked から外す |

## 触らないほうがいいもの

| 対象 | 理由 |
|---|---|
| `docs/archive/**` | historical context。current proof としては読まない前提が既にある |
| `plan/archive/**` | implementation history。plan routing guard で root 再混入を止めている |
| `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md` | 現行 post-MVP 手順としてコードと合っている |
| `docs/strategy_daily_brief/README.md` | 2026-06-22 更新済みで、Daily Brief の Crypto Perp approval boundary がコードと合っている |
| `docs/strategy_workbench_viewer/README.md` | Crypto Perp compact summary と false-only permission flags がコードと合っている |

## 推奨実行順

1. [x] Crypto Perp MVP plan package を archive へ移し、`plan/README.md` と `scripts/check_current_docs.py` の plan routing を更新する。
2. [x] `docs/CURRENT_STATE.md`、`README.md`、`docs/NEXT_DIRECTION_CURRENT.md` の Crypto Perp 文言を、実装済み plan / post-MVP runbook / CLI surface へ寄せる。
3. [x] completion plan / audit を archive へ移し、`README.md` / `CURRENT_STATE.md` / `IMPLEMENTED_SURFACES.md` から current proof として読まれないようにする。
4. [x] assessment docs を current-doc checker 対象に残し、README では Judgment Notes へ下げる。
5. [x] `docs/references/crypto_perp/README.md` を作り、reference notes を current-doc checker 対象に入れる。
6. [ ] tracked `.tmp/live_evidence_*` を現行運用に必要か判断し、不要なら archive または tracked 解除を検討する。

## 残リスク

- archive 配下の本文正誤は今回の対象外。archive は historical context として残す前提。
- `data/` runtime artifact freshness は今回の正本にしていない。fresh checkout では再生成が必要。
- 外部サイトを参照する Crypto Perp reference docs は、2026-06-21 時点の調査メモであり、現在の外部ページ内容までは再確認していない。
- 実ネットワークの Crypto Perp tiny live measurement は未実行。別の明示承認、isolated margin、withdrawal disabled API key、IP restriction、max notional 25 USD、max open positions 1、reduce-only close、flat reconciliation がない限り扱わない。
