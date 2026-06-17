<!--
作成日: 2026-06-18_05:03 JST
更新日: 2026-06-18_05:20 JST
-->

# AI Agent Strategy Backtest Guide

## 結論

この文書は、AI / Codex / LLM が `marketlens-strike` で戦略作成、戦略編集、backtest、結果解釈を進めるための操作契約です。

AI は、コード、CLI help、schema、runtime artifact を正として動きます。docs は入口と説明であり、runtime 値、pass count、hash、phase gate 値の正本ではありません。

この guide で扱う作業は research / paper-only evaluation です。live order、wallet、signing、exchange write、production live readiness claim は扱いません。

## Source Of Truth 順位

1. `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`, `pyproject.toml`, `uv.lock`
2. CLI help: `uv run sis --help` と個別 `uv run sis <command> --help`
3. runtime artifact under `data/`
4. current docs under `docs/`
5. historical docs under `docs/archive/` and `plan/archive/`

判断に迷ったら、先に CLI help と該当 schema / test を読む。古い docs の固定値を現在値として使わない。

## 最初に読むもの

| 目的 | 読むもの |
|---|---|
| repo 全体の現在地 | [CURRENT_STATE.md](CURRENT_STATE.md) |
| AI 向けのこの操作契約 | [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md) |
| 人間向けの戦略・backtest説明 | [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md) |
| Strategy Lab の詳細 | [strategy_research_lab/README.md](strategy_research_lab/README.md) |
| Strategy Authoring の書き方 | [strategy_research_lab/09_STRATEGY_AUTHOR_GUIDE.md](strategy_research_lab/09_STRATEGY_AUTHOR_GUIDE.md) |
| backtest 技術リファレンス | [backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md](backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md) |
| backtest 利用者向け詳細 | [backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md](backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md) |
| Strategy Review | [strategy_review/README.md](strategy_review/README.md) |
| paper observation status | [strategy_lifecycle/README.md](strategy_lifecycle/README.md) |

## 実行してよい標準コマンド

### Baseline input を作る

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
```

用途: local fixture を作る。外部 API、wallet、signing、exchange write は使わない。

### YAML strategy を確認して実行する

```bash
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-explain --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

用途: YAML strategy の validation、説明、signal/backtest artifact 生成。

### Backtest pack を作って読む

```bash
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
uv run sis strategy-backtest-html-report
```

用途: native backtest、suite、benchmark、stress、data availability、baseline、no-lookahead、execution simulation、assumption ledger、comparison、pack validation を一括で確認し、人間が読む HTML / JS report を生成する。

### Review packet を作る

```bash
uv run sis strategy-review-build --review-id <review-id> --replace-existing
uv run sis strategy-review-record --review-dir data/strategy_reviews/<review-id> --decision REVIEWED_FOR_CONTEXT --reviewer <name> --rationale "<why>" --replace-existing
uv run sis strategy-review-record --review-dir data/strategy_reviews/<review-id> --validate-existing
```

用途: 人間が読む review packet と operator review record を作る。これは paper / live permission ではない。

### Paper observation status を読む

```bash
uv run sis strategy-paper-observation-status \
  --data-dir data \
  --canonical-review-path data/research/ndx/paper_observation_review_decision.json \
  --lifecycle-review-path data/research/strategy_lifecycle/strategy_lifecycle_review.json
```

用途: normal paper observation と smoke observation を分けて読む。status artifact は paper intent 生成、paper order 実行、live conversion をしない。

## 読む artifact

| Artifact | 役割 | 主に見る field |
|---|---|---|
| `data/research/strategy_backtest_metrics.json` | 単体 Strategy Authoring backtest 結果 | `summary.trade_count`, `summary.total_return`, `summary.max_drawdown`, `summary.backtest_passed`, `summary.executed_signal_summary` |
| `data/research/backtest_pack/strategy_backtest_pack.json` | pack manifest | `schema_version`, `artifact_manifest`, `external_framework_policy`, no-live flags |
| `data/research/backtest_pack/strategy_backtest_pack_validation.json` | pack validation | `decision`, `failed_count`, `findings`, `permits_live_order`, `live_conversion_allowed` |
| `data/research/backtest_compare/strategy_backtest_comparison.json` | method / suite / robustness の比較 | `method_results`, `suite_results`, `comparison_diagnostics`, `benchmark_relative`, `stress`, `no_lookahead_diff` |
| `data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json` | benchmark 比較 | `summary.strategy_total_return`, `summary.benchmark_total_return`, `summary.active_total_return`, `summary.information_ratio` |
| `data/research/backtest_stress/strategy_backtest_stress.json` | cost / slippage stress | `summary.base_total_return`, `summary.worst_stressed_total_return`, `scenarios` |
| `data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json` | future leakage 検査 | `status`, `summary.checked_signal_count`, `summary.verified_signal_count`, `summary.false_negative_risk` |
| `data/research/backtest_data_availability/backtest_data_availability_ledger.json` | data availability | `summary.total_gap_count`, `summary.future_candidate_count`, `summary.network_used`, `summary.external_api_called` |
| `data/research/backtest_html_report/strategy_backtest_html_report.json` | HTML report manifest | `result_label`, `html_report_path`, `paper_observation_candidate_is_permission`, no-live flags |
| `data/reports/strategy_backtest_html_report.html` | 人間向け HTML / JS report | 損益グラフ、benchmark chart、期間別 trade table、stress summary |
| `data/research/strategy_lifecycle/backtest_acceptance_decision.json` | backtest acceptance | `decision`, `summary_checks`, `boundary_flags` |
| `data/research/strategy_lifecycle/paper_observation_status.json` | paper observation status | `observation_state`, `latest_normal_requirement_gaps`, `normal_thresholds_met`, `permits_live_order`, `live_conversion_allowed` |

欠損 artifact は「未生成」と扱う。存在しない値を推測で補わない。

## Artifact field の読み方

| Field | 一般的な意味 | 禁止解釈 |
|---|---|---|
| `total_return` | 対象期間の合計リターン | 将来も儲かる証明にしない |
| `max_drawdown` | 途中でどれくらい悪化したか | drawdown が小さいだけで安全と断定しない |
| `trade_count` | 評価に使った取引数 | 少ない時は強い結論にしない |
| `backtest_passed` | spec 内の閾値を満たしたか | paper / live 許可にしない |
| `decision=PASS` | その artifact の検査に通った | alpha / paper pass / live readiness にしない |
| `PAPER_OBSERVATION_CANDIDATE` | 次の検証候補 | paper execution permission にしない |
| `permits_live_order=false` | live order を許可しない | true に書き換えない |
| `live_conversion_allowed=false` | live 変換を許可しない | paper/live bridge と読まない |
| `false_negative_risk` | no-lookahead 検査の取りこぼしリスク | risk なしと読まない |

## 結果ラベル

AI が人間に説明する時は、数値だけでなく次のラベルを使う。

| ラベル | 条件の目安 | 次にやること |
|---|---|---|
| 検証不足 | `trade_count` が少ない、artifact 欠損、data availability に gap が多い | 入力 data / sample / suite を増やす |
| 弱い | return はあるが drawdown、stress、regime、rolling stability が悪い | ルール、risk、exit、cost 前提を見直す |
| 要追加検証 | 単発は良いが benchmark、walk-forward、stress、no-lookahead が弱い | pack / suite / no-lookahead / stress を再確認する |
| paper観察候補 | no-lookahead、benchmark、stress、data availability、pack validation が最低限そろう | Strategy Review と paper observation status を通す |

`paper観察候補` は paper 実行許可ではない。次の検証候補という意味に固定する。

## 失敗時の分岐

| 症状 | 先に見るもの | 次の行動 |
|---|---|---|
| `strategy-author-validate` が落ちる | CLI stdout、`strategy-author-explain`、spec YAML | schema / column / feature path / symbol binding を直す |
| `strategy-author-run --through backtest` が落ちる | feature panel、quotes、venue cost matrix | baseline seed を再生成し、入力 path を確認する |
| `strategy-backtest-pack-validate` が FAIL | validation JSON の `findings` | missing / invalid artifact を個別 command で再生成する |
| `trade_count` が少ない | metrics summary、signals count | signal 条件、期間、threshold、universe を見直す |
| stress が悪い | stress scenario と worst return | cost / slippage / exit / position sizing を見直す |
| no-lookahead が弱い | no-lookahead status と `false_negative_risk` | feature availability と timestamp order を確認する |
| paper observation が不足 | `latest_normal_requirement_gaps` | 同日再実行ではなく新しい normal observation evidence を待つ |

## 典型タスク別手順

### 既存 YAML を少し編集する

1. spec を読む。
2. `strategy-author-validate` を実行する。
3. `strategy-author-explain` を実行して人間向け説明を確認する。
4. `strategy-author-run --through backtest` を実行する。
5. `strategy_backtest_metrics.json` と report を読む。
6. 必要なら `strategy-backtest-pack` へ進む。

### Backtest 結果を評価する

1. `strategy-backtest-artifact-summary` を実行する。
2. pack validation が PASS か確認する。
3. native metrics の return / drawdown / trade_count を確認する。
4. benchmark relative を読む。
5. stress / regime split / rolling stability を読む。
6. no-lookahead / data availability / assumption ledger を読む。
7. `strategy-backtest-html-report` を実行し、HTML の結果ラベル、損益グラフ、期間別 trade table を読む。
8. paper / live permission を断定しない。

### Strategy Review に進む

1. 必須 artifact が存在するか確認する。
2. `strategy-review-build` を実行する。
3. `review.md` と `review_manifest.json` を読む。
4. 人間判断を `strategy-review-record` で保存する。
5. `--validate-existing` で path / hash の一致を確認する。

## やってはいけないこと

- `READ_ONLY_GO` を live readiness と読む。
- backtest pass を alpha proof と読む。
- pack validation PASS を paper execution permission と読む。
- `PaperIntentPreview` を live order と読む。
- missing artifact を成功扱いにする。
- runtime hash、pass count、artifact snapshot を tracked doc に current proof として固定する。
- Bitget / Hyperliquid を current Strategy Lab venue として schema widening なしに扱う。
- wallet、signing、exchange write、live order path をこの guide の範囲で進める。

## HTML / visual report の扱い

現行 repo には、依存追加なしで既存 artifact を読む `strategy-backtest-html-report` があります。

```bash
uv run sis strategy-backtest-html-report
```

出力:

- `data/research/backtest_html_report/strategy_backtest_html_report.json`: HTML report の manifest。source artifact path / hash、結果ラベル、no-live boundary を持つ。
- `data/reports/strategy_backtest_html_report.html`: ブラウザで開く人間向け report。損益グラフ、benchmark 比較、指定期間の trade table、stress summary を表示する。

この command は既存 artifact を読む read-only renderer です。live order、wallet、signing、exchange write に接続しない。HTML の `paper観察候補` ラベルも paper 実行許可ではなく、次の検証候補という意味だけに固定する。
