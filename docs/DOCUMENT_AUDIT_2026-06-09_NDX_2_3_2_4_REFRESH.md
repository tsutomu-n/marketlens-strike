<!--
作成日: 2026-06-09_14:23 JST
更新日: 2026-06-09_14:23 JST
-->

# Code-Truth Documentation Audit 2026-06-09

この文書は 2026-06-09_14:23 JST 時点のコード、CLI、config、schema、tests、current-doc checker を正として、NDX Layer 2.3/2.4 実装後に更新できるドキュメント、古い内容があるドキュメント、作り直したほうがよいドキュメント、削除・archive 候補を分類する。

## 確認した正本

確認コマンド:

```bash
git status --short --branch --untracked-files=all
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```

確認した実装面:

```text
src/sis/commands/research.py
src/sis/research/dag/
src/sis/research/ndx/
configs/research_layer_2_2/ndx/
configs/research_layer_2_3/ndx/
configs/research_layer_2_4/ndx/
schemas/layer_2_2_*.schema.json
schemas/ndx_*.schema.json
tests/research/
scripts/check_current_docs.py
```

現行事実:

```text
root CLI:
  research-layer22-validate / export / review-pack / review-import / exit-gate が存在する。
  research-ndx-source-resolve / feature-panel / residual / diagnostics / residual-validate が存在する。

Layer 2.2:
  local/manual review gate。
  APPROVE_2_3 は second_review_required=false、unresolved_human_decisions=[]、blocker_count=0 の時だけ成立。
  REVISE_2_2 / REJECT_SEED では freeze manifest を生成せず、同じ output directory の古い freeze manifest も削除する。

Layer 2.3:
  fixture-first source resolution、feature panel、open-gap residual、diagnostics / neutralization pre-report、counter-DAG refutation skeleton を作る。
  same-day close leakage、per-source timestamp、source_ts_max <= feature_ts、DAG lineage を検査する。

Layer 2.4:
  residual validation gate。
  現在の default fixture artifacts は REVISE_2_3 with INSUFFICIENT_VALIDATION_ERAS and INSUFFICIENT_VALIDATION_SAMPLE。
  これは Strategy Lab export approval ではない。

latest verification snapshot:
  ./scripts/check passed; Python 3.13.7; docs checker checked 101 current docs; pyrefly 0 errors; ty passed; 936 passed.
```

## 更新したドキュメント

| Path | 更新内容 |
|---|---|
| `README.md` | NDX 2.2/2.3/2.4 の read order、CLI flow、current boundaries、verification snapshot を更新。 |
| `docs/research/ndx/README.md` | NDX directory 入口を 2.2 only から 2.2 -> 2.3 -> 2.4 に更新。 |
| `docs/CURRENT_STATE.md` | NDX 2.3/2.4 implemented surfaces、schemas、artifact再生成、現在の `REVISE_2_3` 境界を追加。 |
| `docs/CODE_STATUS.md` | NDX 2.3/2.4 行、未実装の 2.5 export 境界、current verification を追加。 |
| `docs/ARCHITECTURE_AND_PHASES.md` | `research.dag` と `research.ndx` の責務を分離し、2.3/2.4 flow を追加。 |
| `docs/OPERATIONS_RUNBOOK.md` | 2.3/2.4 local artifact regeneration と stop conditions を追加。 |
| `docs/DOCS_LINT_POLICY_2026-05-30.md` | current audit の allowlist を本書へ切り替え。 |
| `docs/archive/README.md` | 2026-06-09 の旧監査 archive routing を追記。 |
| `plan/README.md` | 実装済み Layer 2.2 acceptance hardening / Layer 2.3 plan pack を historical contract として整理。 |

## 古い内容があったドキュメント

| Path | 古い内容 | 扱い |
|---|---|---|
| `docs/DOCUMENT_AUDIT_2026-06-08_CODE_TRUTH_REFRESH.md` | 2.3開始前の監査、古い verification snapshot、Layer 2.2 only のNDX入口。 | `docs/archive/2026-06-09-ndx-doc-refresh/` へ移動。 |
| `README.md`, `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md` | NDXが2.2止まりに読める説明、古い verification snapshot。 | 更新済み。 |
| `docs/ARCHITECTURE_AND_PHASES.md` | `research.dag` が feature/residual を扱わない説明だけで、`research.ndx` が未記載。 | 更新済み。 |
| `docs/OPERATIONS_RUNBOOK.md` | feature panel / residual / neutralization を2.2の停止条件としてだけ扱っていた。 | 2.3/2.4 section を追加。 |
| `docs/research/ndx/README.md` | read order とcommandsが2.2 only。 | 更新済み。 |

## 作り直したほうがよいドキュメント

| Path | 理由 | 作り直し案 |
|---|---|---|
| `docs/CURRENT_STATE.md` | 現行能力一覧が肥大化し、current state、capability、runtime snapshot が混在している。 | 短い state index に作り直し、詳細capabilityは専用docsへ逃がす。 |
| `docs/CODE_STATUS.md` | migration PR、post-pivot、NDX gates、runtime readiness が1表に積み上がっている。 | implemented surface matrix と known boundary matrix に分ける。 |
| `docs/OPERATIONS_RUNBOOK.md` | root restart、NDX、Trade[XYZ] collection、Strategy Lab、paper ops が同居している。 | root runbook + domain runbooks に分割する。 |
| `docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md` | Layer 2.2実装記録に後続の受入監査や次phase情報が追記され続けている。 | Layerごとの implementation record を分ける。 |

## 削除・archive 候補

削除ではなく archive 維持を推奨する。過去判断の証跡として有用なため。

| Path | 推奨 | 理由 |
|---|---|---|
| `plan/archive/2026-06-09-ndx-plan-routing/feature_expansion_plan_20260608_layer_2_2_acceptance_hardening_v1/` | archive済み | 実装済み acceptance hardening contract。current proof は code/tests/schema/docs。 |
| `plan/archive/2026-06-09-ndx-plan-routing/feature_expansion_plan_20260608_layer_2_3_ndx_preflight_feature_residual_v1/` | archive済み | 実装済み Layer 2.3 contract。current proof は code/tests/schema/docs。 |
| `plan/0608ここからの計画/*.zip` | archive / ignored source package | `.gitignore` の `*.zip` 対象。tracked current proof ではない。 |
| `plan/0608ここからの計画/01_layer_2_2_foundation/` | archive / ignored source package | 旧 v2 ZIP は historical design background。新規実装指示ではない。 |
| `plan/0608ここからの計画/02_layer_2_2_exit_gate/` | archive / ignored source package | 旧 v5 ZIP は historical design background。新規実装指示ではない。 |

## 残リスク

```text
1. CURRENT_STATE / CODE_STATUS / OPERATIONS_RUNBOOK はまだ短文化までは未実施。
2. current verification snapshot は作業時点の観測値であり、将来は再実行コマンドを正とする。
3. Layer 2.4 はまだ APPROVE_STRATEGY_LAB_EXPORT ではない。2.5 Strategy Lab research-only export、strategy_signals.parquet、backtest、paper candidate へ進んだとは読まない。
4. ignored ZIP は git 管理外なので、tracked diff だけでは移動履歴を完全には保持しない。
```
