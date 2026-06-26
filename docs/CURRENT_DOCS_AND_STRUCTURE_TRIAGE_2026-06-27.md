<!--
作成日: 2026-06-27_07:30 JST
更新日: 2026-06-27_07:30 JST
-->

# Current Docs And Structure Triage 2026-06-27

## 結論

この文書は `marketlens-strike` の現在のドキュメント配置とディレクトリ構造だけを扱う。過去の状態、過去の pass 数、過去の branch 状態、過去の artifact snapshot はここに置かない。

今の正本は `src/`、`tests/`、`schemas/`、`configs/`、`scripts/`、`.github/workflows/ci.yml`、`pyproject.toml`、`.python-version`、`uv.lock`、CLI help である。docs は入口、説明、runbook、判断補助であり、runtime 値や readiness の正本ではない。

現在の docs は機械検証上は壊れていない。`scripts/check_current_docs.py` は current docs 162 件を検査し、`scripts/check_cli_catalog.py` は public CLI 208 件を Typer 登録と照合している。

## 現在の実装構造

| 領域 | 現在の場所 | 役割 |
|---|---|---|
| CLI root | `src/sis/cli.py` | `sis` Typer root app。public command surface の入口。 |
| CLI command wrappers | `src/sis/commands/` | CLI 引数、入出力、report command の薄い wrapper。 |
| Backtest | `src/sis/backtest/`, `src/sis/backtest/engine/`, `src/sis/backtest/trade_xyz/` | strategy backtest、artifact pack、optional framework contracts、Trade[XYZ] pure backtest surface。 |
| Research / NDX | `src/sis/research/`, `src/sis/research/dag/`, `src/sis/research/ndx/`, `configs/research_layer_2_2/ndx`, `configs/research_layer_2_3/ndx`, `configs/research_layer_2_4/ndx` | NDX local research gates、DAG、feature/residual/paper-observation flow。 |
| Strategy Lab / Authoring | `src/sis/research/strategy_lab/`, `docs/strategy_research_lab/examples/` | Strategy Lab artifacts、YAML authoring、paper-only evaluation。 |
| Strategy operation loop | `src/sis/strategy_*` directories | input, feedback, stage, smoke, runtime observation, drift, learning, case lite/index, daily brief, AI review, model loop, micro-live plan, scale decision, viewer。 |
| Crypto Perp | `src/sis/crypto_perp/`, `src/sis/crypto_perp/bitget/`, `configs/crypto_perp/` | truth-cycle artifact chain、Bitget public/account/order-preview/tiny-live guarded surfaces。 |
| Venue / execution / paper | `src/sis/venues/`, `src/sis/execution/`, `src/sis/paper/` | Trade[XYZ] read-only surfaces、execution state、paper operation artifacts。 |
| Reports / operations | `src/sis/reports/`, `src/sis/ops/`, `src/sis/state/` | phase gate、operations dashboard/bundle/timeline、audit/remediation/readiness reports。 |
| Schemas | `schemas/` | JSON artifact contracts。現在 143 files。 |
| Tests | `tests/` | domain 別 pytest。`tests/backtest/`, `tests/strategy_authoring/`, `tests/crypto_perp/`, `tests/strategy_*` が主要 slice。 |
| Runtime state | `data/`, `logs/`, `.tmp/` | generated/runtime state。fresh checkout の正本ではない。 |
| Docs | `docs/` | current docs、runbooks、guides、reference、archive。 |
| Plans | `plan/` | active/historical implementation contracts。current proof ではない。 |

## 現在の docs 配置

| docs 領域 | 現在の役割 |
|---|---|
| `README.md` | repo 入口。主要 docs への read order。 |
| `docs/CURRENT_STATE.md` | 現在地の短い入口。 |
| `docs/APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md` | 非技術者向け説明。 |
| `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` | 詳細説明。大きいため将来の分割候補。 |
| `docs/CODE_STATUS.md` | code/status の誤読防止。 |
| `docs/IMPLEMENTED_SURFACES.md` | 実装済み surface map。 |
| `docs/NEXT_DIRECTION_CURRENT.md` | 次方向と外部入力時の再確認入口。 |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | 技術向け capability index。 |
| `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md` | 平易な capability 説明。 |
| `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` | public CLI catalog。CLI 変更時に更新する。 |
| `docs/backtest/` | backtest guide/reference/non-goals/Trade[XYZ] pure backtest docs。 |
| `docs/research/ndx/` | NDX research gates の current docs。 |
| `docs/strategy_research_lab/` | Strategy Lab / Strategy Authoring docs と examples。 |
| `docs/strategy_*` | Strategy operation loop の各 artifact surface docs。 |
| `docs/runbooks/` | operator runbooks。 |
| `docs/venues/` | venue boundary docs。 |
| `docs/references/crypto_perp/` | Crypto Perp reference / adoption decisions。 |
| `docs/algo/` | strategy ideas / parts / factory docs。 |
| `docs/archive/` | historical docs。current proof として読まない。 |
| `docs/plans/` | 現在 tracked file なし。 |
| `plan/2026-06-22-strategy-feedback-case-index/` | 現在 allowlist された active plan package。 |
| `plan/archive/` | historical plans。current proof として読まない。 |

## 更新できるドキュメント

以下は現行 docs として維持し、コードや CLI が変わった時に同じ pass で更新する。

| 対象 | 今の扱い | 更新条件 |
|---|---|---|
| `README.md` | 入口として維持。 | read order、主要 surface、setup command が変わった時。 |
| `docs/CURRENT_STATE.md` | 現在地の短い入口として維持。 | product axis、外部入力、主要 surface が変わった時。 |
| `docs/CODE_STATUS.md` | safety/readiness の誤読防止として維持。 | readiness boundary や exposed operator path が変わった時。 |
| `docs/IMPLEMENTED_SURFACES.md` | 実装済み surface map として維持。 | CLI、schema、tests、domain surface が増減した時。 |
| `docs/NEXT_DIRECTION_CURRENT.md` | 次方向の入口として維持。 | 次に進める作業や外部入力 checklist が変わった時。 |
| `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` | CLI catalog として維持。 | `scripts/check_cli_catalog.py` の照合結果が変わる CLI 追加/削除時。 |
| `docs/runbooks/README.md` | operator route table として維持。 | runbook が増減した時。 |
| `docs/backtest/README.md` | backtest 入口として維持。 | backtest CLI、artifact schema、optional framework surface が変わった時。 |
| `docs/research/ndx/README.md` | NDX research 入口として維持。 | NDX layer/config/CLI が変わった時。 |
| `docs/strategy_research_lab/README.md` | Strategy Lab / Authoring 入口として維持。 | authoring schema、examples、CLI flow が変わった時。 |

## 古い内容があるドキュメント

以下は current proof ではない。過去値や判断補助を含む可能性があるため、現行判断では必ず code、CLI、schema、tests、current runtime artifact を先に見る。

| 対象 | 今の扱い | 推奨 |
|---|---|---|
| `docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md` | 判断補助。正本ではない。 | 残す。冒頭の非正本注意を強める余地あり。 |
| `docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md` | 判断補助。正本ではない。 | 残す。冒頭の非正本注意を強める余地あり。 |
| `docs/MIGRATION_HISTORY.md` | 実装履歴。正本ではない。 | 残す。current readiness へリンクしない。 |
| `docs/DOCUMENT_AUDIT_2026-06-22_CODE_TRUTH_TRIAGE.md` | 過去 audit。 | 残す。最新入口にはしない。 |
| `docs/DOCUMENT_AUDIT_2026-06-26_CODE_TRUTH_DOC_TRIAGE.md` | 直近 audit。 | 残す。次回以降はこの文書を現在-only 入口にする。 |
| `docs/final-summary.md` | merge summary。 | 残す。current proof ではなく merge 時点の要約として読む。 |
| `docs/archive/**` | historical context。 | current proof として読まない。 |
| `plan/archive/**` | historical implementation plan。 | current proof として読まない。 |

## 作り直したほうがいいドキュメント

以下は壊れているという意味ではない。今の構造では 1 本に役割が集まりやすく、次に触る時は分割や再構成のほうが局所更新より安全。

| 対象 | 今の問題 | 作り直し方 |
|---|---|---|
| `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` | 利用者向け説明、技術用語、surface detail が 1 本に集まっている。 | current overview、technical glossary、artifact/schema reference に分ける。 |
| `docs/trade_xyz_bot_beginner_guide.md` と `docs/trade_xyz_bot_beginner_guide.html` | Trade[XYZ] 固有 guide と repo 全体の初心者入口が混ざりやすい。 | Trade[XYZ] 固有 guide と venue-neutral beginner guide を分ける。 |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md` | capability detail と operator guide が重なりやすい。 | capability reference と execution guide に分ける。 |
| `docs/runbooks/README.md` | runbook 入口としてさらに強化できる。 | operator が目的別に辿れる route table へ整理する。 |

## 削除・アーカイブしてもよいドキュメント

現時点で即削除すべき tracked docs はない。削除より archive 維持を優先する。

| 対象 | 今の扱い | 推奨 |
|---|---|---|
| `docs/archive/**` | archive 済み。 | 削除しない。公開配布や容量問題が出た時だけ別途 archive slimming。 |
| `plan/archive/**` | archive 済み。 | 削除しない。current proof として読まない。 |
| `docs/live_evidence_reports/` に生成される report | source doc ではない。 | tracked に戻す場合は archive か `data/` artifact 扱いにする。 |
| `plan/0607ここからの計画2/*.zip`, `plan/0608ここからの計画/**/*.zip`, `plan/0621ここから01/*.zip` | untracked ZIP。 | 中身確認なしに削除しない。使わないなら別途削除判断。 |
| 空の `docs/plans/` | tracked file なし。 | Git 上は保持不要。新しい current plan を置くなら `plan/` 側の routing と合わせる。 |

## 今の推奨 read order

1. `README.md`
2. `docs/CURRENT_STATE.md`
3. `docs/CODE_STATUS.md`
4. `docs/IMPLEMENTED_SURFACES.md`
5. `docs/NEXT_DIRECTION_CURRENT.md`
6. `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
7. 作業領域別 docs:
   - Backtest: `docs/backtest/README.md`
   - NDX: `docs/research/ndx/README.md`
   - Strategy Lab: `docs/strategy_research_lab/README.md`
   - Strategy Review: `docs/strategy_review/README.md`
   - Crypto Perp: `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
   - Venue boundary: `docs/venues/read_only_capability_probe.md`

## 今の verification

現在の docs / CLI の最低確認:

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
```

広い確認:

```bash
./scripts/check
```

この文書には固定の pytest pass count、runtime hash、phase gate result、artifact snapshot を置かない。それらは作業時点で再実行して確認する。
