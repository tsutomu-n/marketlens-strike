<!--
作成日: 2026-07-02_20:36 JST
更新日: 2026-07-02_20:45 JST
-->

# T6 Implementation Plan

## 結論

T6ではBacktest Kill Gateを追加する。既存backtest artifactから明示的に読めるmetricだけを抽出し、読めない値は推定せず `NOT_ESTIMABLE` と `INCONCLUSIVE_DATA` に落とす。backtest passだけではpaper/live/virtual進行許可を出さない。

## チェックポイントID

CP5 / PR #17 T6

## 目的

候補をbacktestで「攻める許可」にせず、NO_TRADE比較、stress、loss、multiplicity、source不足で殺すか止めるgateにする。

## 現状

- CP1で `BacktestKillGate` model/schemaは追加済み。
- CP4でmultiplicity accountは生成可能。
- 既存backtest系schemaはsummary自由度が高いものがあり、抽出不能metricが起きる。

## 制約

- backtestを実行しない。
- missing metricを推定で埋めない。
- `SHORTLIST_FOR_VIRTUAL` はT6単体では出さず、全部passでも `RESEARCH_ONLY` に留める。
- public commandは `edge-candidate-backtest-kill-gate` のみ追加する。
- paper/live/wallet/signing/exchange writeは常にfalse。

## 対象ファイル

新規:

- `src/sis/edge_candidate_factory/backtest_inputs.py`
- `src/sis/edge_candidate_factory/backtest_kill_gate.py`
- `tests/edge_candidate_factory/test_backtest_inputs.py`
- `tests/edge_candidate_factory/test_backtest_kill_gate.py`

変更:

- `src/sis/commands/edge_candidate_factory.py`
- `src/sis/edge_candidate_factory/__init__.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`

## 実装方針

1. `backtest_inputs.py` はJSON objectを読み、known keyからmetricを抽出する。
2. 明示fieldが無いmetricは `None` とし、not-estimable reasonを残す。
3. `backtest_kill_gate.py` は `BacktestKillGateInputs` と `build_backtest_kill_gate()` を持つ。
4. event thresholdは `common_rule=100`、medium family=30、rare dislocation=10 とする。
5. after-cost/no-trade負け、stress負け、largest loss超過、profit concentration超過は `KILL`。
6. source不足または必須metric不足は `INCONCLUSIVE_DATA`。
7. bridge technical readiness不足、execution precheck失敗、unexecutable reasonありは `INCONCLUSIVE_DATA`。
8. 全条件passでも `RESEARCH_ONLY` とし、virtual gateへ進める許可は出さない。

## 実装手順

1. RED: backtest input extractionとkill gate判定のfocused testsを追加する。
2. GREEN: `backtest_inputs.py` を追加する。
3. GREEN: `backtest_kill_gate.py` を追加する。
4. GREEN: CLI commandとcatalogを追加する。
5. VERIFY: focused tests、CLI help、schema validation、CLI catalog、full checkを確認する。

## テスト方針

```bash
uv run pytest tests/edge_candidate_factory/test_backtest_inputs.py tests/edge_candidate_factory/test_backtest_kill_gate.py -q
uv run pytest tests/edge_candidate_factory -q
uv run sis edge-candidate-backtest-kill-gate --help
uv run python scripts/check_cli_catalog.py
uv run ruff check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py tests/edge_candidate_factory
uv run ruff format --check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py tests/edge_candidate_factory
uv run pyrefly check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py
uv run ty check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py --python-version 3.13 --output-format concise
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## 完了条件

- Backtest passだけでは `SHORTLIST_FOR_VIRTUAL` にならない。
- NO_TRADEに負ける候補は `KILL` になる。
- source不足は `INCONCLUSIVE_DATA` になる。
- bridge/execution blockerは `INCONCLUSIVE_DATA` になる。
- rare event familyはevent count不足だけで即KILLせず `RESEARCH_ONLY` または `INCONCLUSIVE_DATA` に落ちる。
- 抽出不能metricは `NOT_ESTIMABLE` conditionになる。
- CLI catalog checkerが通る。

## 失敗条件

- missing metricを0や推定値で埋める。
- backtest passをvirtual/paper/live readinessと誤読させる。
- source不足をKILLにしてcandidate自体の失敗と混同する。
- CLIがexchange writeやnetworkを使う。

## 影響範囲

edge_candidate_factoryのBacktest Kill Gate module、既存command moduleへのcommand追加、CLI catalog、testsのみ。

## ロールバック方針

T6追加module/tests、command registration、CLI catalog行、plan docを戻す。

## 代替案

- 代替案A: 既存backtest schemaごとに専用parserを深く作る。T6には重く、未使用artifact推定を誘発する。
- 代替案B: metric不足でもpass扱いする。gateの意味が壊れる。
- 採用案: known key抽出 + missingはnot estimable。

## 未解決事項

なし。このチェックポイントの範囲ではユーザー判断は不要。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-smart-priors-20260702-1952`

## 移行手順

なし。

## 批判レビュー1

- 既存backtest artifactのsummaryは固定schemaではない。parserは広く読みすぎず、明示keyだけ読む。
- `SHORTLIST_FOR_VIRTUAL` を出すとT8のvirtual gateを飛ばす誤読が起きる。T6は最大でも `RESEARCH_ONLY`。
- rare event familyはevent countだけで殺さず、metric不足と組み合わせて研究止まりにする。

## 批判レビュー2

- source availability不足はcandidateの経済性ではなく検証不能問題。`INCONCLUSIVE_DATA` に落とす。
- NO_TRADE比較が無い場合にafter-cost edgeだけでpassさせない。
- multiplicity accountが無い場合は `INCONCLUSIVE_DATA`。探索会計なしのbacktest passを許さない。
- bridge technical readiness、execution precheck、unexecutable reason countは経済性のpass/failとは別の実装不能リスク。pass扱いせず `INCONCLUSIVE_DATA` に落とす。
