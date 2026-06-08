<!--
作成日: 2026-06-08_18:21 JST
更新日: 2026-06-08_18:21 JST
-->

# Code-Truth Documentation Audit 2026-06-08

この文書は 2026-06-08_18:21 JST 時点のコード、CLI、config、schema、tests、current-doc checker を正として、更新できるドキュメント、古い内容があるドキュメント、作り直したほうがよいドキュメント、削除・archive 候補を分類する。

## 確認した正本

確認コマンド:

```bash
git status --short --branch --untracked-files=no
uv run sis --help
uv run python scripts/check_current_docs.py
```

確認した実装面:

```text
src/sis/cli.py
src/sis/commands/
src/sis/research/dag/
src/sis/research/strategy_lab/
src/sis/backtest/
src/sis/venues/trade_xyz/
src/sis/execution/
schemas/
configs/research_layer_2_2/ndx/
scripts/check_current_docs.py
```

現行事実:

```text
current docs checker:
  checked 99 current docs: metadata, links, EOF, and legacy roots ok

root CLI:
  research-layer22-validate / export / review-pack / review-import / exit-gate が存在する。
  research-dag-validate / export も legacy/general DAG command として存在する。
  Strategy Lab, Strategy Authoring, paper, Trade[XYZ], operations commands は引き続き存在する。

default scope:
  backtest-first / venue-neutral。
  NDX research は Layer 2.2 DAG foundation と manual review gate を入口にする。
  Trade[XYZ] は実装済み venue / historical read-only context だが、default product axis ではない。

Layer 2.2 review harness:
  local/manual review plumbing only。
  external API、credentials、feature panel、residual calculation、neutralization、Strategy Lab export、backtest、paper/live order は対象外。
```

## 実施済みの整理

2026-06-08 に実行済み:

```text
docs/archive/2026-06-08-doc-routing/
  root Trade[XYZ] collection/status/audit docs
  docs/algo/obsidian_note_copies/
  docs/algo/obsidian_note_rewrites_2026-05-28/
  docs/集めるべき実データ0531-2108/
  docs/DOCUMENT_AUDIT_2026-06-06_CODE_TRUTH_REFRESH.md
  docs/DOCUMENT_CLEANUP_EXECUTION_PLAN_2026-06-06.md

plan/archive/2026-06-08-plan-routing/
  2026-06-07 Layer 2.2 plan packs
  top-level Trade[XYZ] plan docs
  marketlens_strategy_research_lab_migration_pack/
```

## 更新できるドキュメント

| Path | 理由 | 更新内容 |
|---|---|---|
| `README.md` | 冒頭と read order は現行主軸を示す入口。 | Layer 2.2 / NDX review gate を先に読み、Trade[XYZ] は専用 flow と boundary に残す。古い fixed pass count は snapshot として日付付きに限定する。 |
| `AGENTS.md` | repo-local restart / scope default の入口。 | Layer 2.2 review harness の3 command と、local/manual review only の境界を残す。 |
| `docs/CURRENT_STATE.md` | current state と capability list が混在し、長くなっている。 | 直近では Layer 2.2 v3 Minimal と archive routing を反映済み。次は capability 列挙を Strategy docs へ逃がして短くする。 |
| `docs/CODE_STATUS.md` | PR migration status、post-PR status、runtime readiness が混在している。 | 実装済み surface 表へ寄せ、runtime/data readiness は `CURRENT_STATE` または dedicated readiness doc へ逃がす。 |
| `docs/OPERATIONS_RUNBOOK.md` | Trade[XYZ] collection と NDX Layer 2.2 review gate が同居している。 | root runbook は入口だけにし、NDX / Trade[XYZ] / Strategy Lab / paper ops を分割候補にする。 |
| `docs/research/ndx/README.md` | NDX docs の新入口。 | 現状維持。次に Layer 2.3 が始まる時だけ read order と boundary を更新する。 |
| `docs/DOCS_LINT_POLICY_2026-05-30.md` | strict check 対象一覧が 2026-06-08 の allowlist とズレていた。 | この監査で更新対象。current docs checker の実リストに合わせる。 |
| `docs/archive/README.md` | archive routing の索引。 | この監査で 2026-06-08 の追加 archive を追記する。 |

## 古い内容があるドキュメント

| Path | 古い内容 | 扱い |
|---|---|---|
| `docs/archive/2026-06-08-doc-routing/DOCUMENT_AUDIT_2026-06-06_CODE_TRUTH_REFRESH.md` | 2026-06-06 時点の分類で、実行後の archive 状態や Layer 2.2 v3 Minimal を正にしていない。 | historical audit として archive 済み。current classification は本書を使う。 |
| `docs/archive/2026-06-08-doc-routing/DOCUMENT_CLEANUP_EXECUTION_PLAN_2026-06-06.md` | 「archive 移動は未実施」など、現在は完了済みの手順が残る。 | historical execution plan として archive 済み。 |
| `docs/DOCUMENT_AUDIT_2026-05-31.md` | 2026-05-31 時点の audit。古い pass count を説明として含む。 | historical value はあるが current read order 先頭には置かない。 |
| `docs/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md` | 2026-05-31 backtest update 時点の audit。 | historical backtest update record として残す。 |
| `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md` | Strategy Lab audit/spec として有用だが、全体 docs audit の正本ではない。 | Strategy Lab 専用入口として残し、全体 audit は本書へ寄せる。 |
| `docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md` | filename は 2026-06-07 だが、2026-06-08 の v3 Minimal も追記済み。 | current docs としては許容。次の大きな変更時は新しい record に分ける。 |
| `pyproject.toml` | project description が `Trade[XYZ] research...` を先頭に置く。これは docs ではなく package metadata だが、README 冒頭とはズレる。 | dependency 変更なしで直せる別 scope の metadata 更新候補。 |

## 作り直したほうがいいドキュメント

| Path | 理由 | 作り直し案 |
|---|---|---|
| `docs/CURRENT_STATE.md` | 現行能力一覧が肥大化し、read order / runtime state / Strategy Authoring capability list が混在している。 | 2ページ相当の短い state に作り直し、capability は `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` へリンクする。 |
| `docs/CODE_STATUS.md` | migration PR、post-pivot、Layer 2.2、runtime readiness が1表に積み上がっている。 | `Implemented Surfaces` と `Known Boundaries` だけの表へ再構成する。 |
| `docs/OPERATIONS_RUNBOOK.md` | 1本に operations / Trade[XYZ] collection / NDX review / Strategy Lab / Bitget demo が入っている。 | root runbook + domain runbooks に分割する。 |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` | capability list が長く、schema / tests との drift risk が高い。 | human summary + generated/source-map appendix へ分ける。 |
| `docs/trade_xyz_bot_beginner_guide.html` | useful guide だが current product axis ではない。 | current boundary banner を追加するか、Trade[XYZ] guide index へ分離する。 |

## 削除・archive してもよいドキュメント

削除ではなく archive 済み / archive 維持を推奨する。過去判断の証跡として有用なため。

| Path | 推奨 | 理由 |
|---|---|---|
| `docs/archive/2026-06-08-doc-routing/TRADE_XYZ_*.md` | archive 維持 | Trade[XYZ] collection/status/audit の historical record。 |
| `docs/archive/2026-06-08-doc-routing/集めるべき実データ0531-2108/` | archive 維持 | 実データ定義の historical snapshot。current status ではない。 |
| `docs/archive/2026-06-08-doc-routing/algo/obsidian_note_copies/` | archive 維持 | source snapshot。current docs lint 対象にしない。 |
| `docs/archive/2026-06-08-doc-routing/algo/obsidian_note_rewrites_2026-05-28/` | archive 維持 | 旧 rewrite。2026-05-29 rewrite を current reference とする。 |
| `plan/archive/2026-06-08-plan-routing/0607ここからの計画*/` | archive 維持 | Layer 2.2 実装済み plan pack。current status は code/docs/research/ndx を使う。 |
| `plan/archive/2026-06-08-plan-routing/TRADE_XYZ_*.md` | archive 維持 | Trade[XYZ] plan history。default next action ではない。 |
| `plan/archive/2026-06-08-plan-routing/marketlens_strategy_research_lab_migration_pack/` | archive 維持 | migration contract。current venue/schema contract として読ませない。 |

## Better にした点

今回の追加調査で、単なる分類ではなく次を実行した。

```text
1. 2026-06-06 audit / cleanup plan を archive へ移動。
2. 本書を 2026-06-08 時点の current docs audit として追加。
3. current-doc checker の allowlist を本書へ切り替え。
4. docs lint policy と README read order を最新化。
5. Layer 2.2 semantic drift marker を checker に残し、旧 CLI / 旧 temporal label の再混入を防止。
```

## 残リスク

```text
1. pyproject.toml の description は package metadata なので、この docs audit では未変更。
2. CURRENT_STATE / CODE_STATUS / OPERATIONS_RUNBOOK はまだ作り直し候補で、短文化までは未実施。
3. Strategy Lab capability docs は厚く、今後 schema/tests 由来の source-map 化が望ましい。
4. `research-dag-validate` / `research-dag-export` は CLI に残る。これは旧専用入口ではなく general DAG command として扱う。
```
