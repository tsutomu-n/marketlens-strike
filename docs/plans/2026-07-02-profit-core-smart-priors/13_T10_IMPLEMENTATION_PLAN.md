<!--
作成日: 2026-07-02_21:08 JST
更新日: 2026-07-02_21:08 JST
-->

# T10 Implementation Plan

## 結論

T10では外部LLM APIを呼ばず、local adversarial packet build と manual response import を追加する。正式artifactは `llm_adversarial_evidence_review.v1` とし、approval文言は必ず無視し、paper/live/actual-cash/gate overrideを許可しない。

## チェックポイントID

CP9 / PR #17 T10

## 目的

候補volume増加時のnarrative creep、missing artifact、contradiction、overclaimを検出し、人間レビューに渡す。ただしLLMを採用者やgate override主体にしない。

## 現状

- CP1で `LLMAdversarialEvidenceReview` model/schemaは追加済み。
- model validatorは hard/soft finding count の整合を検査する。
- packet build / manual import command は未実装。

## 制約

- 外部LLM APIを呼ばない。
- LLM approval、paper/live permission、actual cash decision、gate overrideを許可しない。
- packetはv0補助artifactとし、新規schema追加はしない。
- official outputは `llm_adversarial_evidence_review.v1` のみ。

## 対象ファイル

新規:

- `docs/plans/2026-07-02-profit-core-smart-priors/13_T10_IMPLEMENTATION_PLAN.md`
- `src/sis/edge_candidate_factory/adversarial_review.py`
- `tests/edge_candidate_factory/test_adversarial_review.py`

変更:

- `src/sis/commands/edge_candidate_factory.py`
- `src/sis/edge_candidate_factory/__init__.py`
- `tests/edge_candidate_factory/test_cli.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`

## 実装方針

1. `build_adversarial_packet()` はsource pathsから local packet JSONを作る。
2. missing sourceはpacket内で `exists=false`、`sha256=ZERO_HASH` として保存する。
3. `import_adversarial_review()` はpacketとmanual response JSONを読み、`LLMAdversarialEvidenceReview` を返す。
4. packet内 missing source は machine-checkable hard findingに変換する。
5. manual response findingsはenumに合う範囲だけ取り込む。
6. manual responseにapproval文言があっても `llm_approval_ignored=true`、permission/override fieldsはfalse固定。
7. hard blockerは `severity=hard` または `hard_blocker=true` のfindingだけにする。

## 実装手順

1. RED: packet build/import testsとCLI help/write testsを追加する。
2. GREEN: `adversarial_review.py` を追加する。
3. GREEN: CLI commandsとcatalogを追加する。
4. VERIFY: focused tests、schema validation、CLI catalog、full checkを確認する。

## テスト方針

```bash
uv run pytest tests/edge_candidate_factory/test_adversarial_review.py tests/edge_candidate_factory/test_cli.py -q
uv run pytest tests/edge_candidate_factory -q
uv run sis edge-candidate-adversarial-packet-build --help
uv run sis edge-candidate-adversarial-import --help
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

- manual responseにapproval文言があっても、artifactはpermissionを出さない。
- missing source refsがある場合、findingとして保存される。
- machine-checkableな欠落だけをhard blockerにできる。
- public CLIはpacket build/importのhelpが通り、stdout safety fieldsを出す。

## 失敗条件

- 外部LLM APIを呼ぶ。
- LLM文言からpaper/live/actual-cash/gate permissionを出す。
- missing artifactを補完したことにする。
- hard/soft countsをmanual input任せにする。

## 影響範囲

edge_candidate_factoryのadversarial review module、既存command moduleへのcommand追加、CLI catalog、testsのみ。

## ロールバック方針

T10追加module/tests、command registration、CLI catalog行、plan docを戻す。

## 代替案

- 代替案A: 既存 Strategy AI Review subsystem に寄せる。汎用レビュー機能は大きく、T10のartifact contractからずれるため不採用。
- 代替案B: LLM API callまで実装する。外部送信と認証境界が増えるため禁止。
- 採用案: local packet + manual import + strict review artifact。

## 未解決事項

なし。このチェックポイントの範囲ではユーザー判断は不要。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-smart-priors-20260702-1952`

## 移行手順

なし。

## 批判レビュー1

- packet schemaを増やすとT10の契約が膨らむ。正式検証対象はreview artifactに限定する。
- approval文字列の検出は安全境界の補助であり、採用判断には使わない。常に `llm_approval_ignored=true`。
- missing sourceはmachine-checkable hard findingにできるが、narrative overclaimはsoft/human review寄りに扱う。

## 批判レビュー2

- manual responseのcountsを信用すると改ざんや記入ミスで壊れる。import側でcountsを再計算する。
- source fileが無い場合でもpacket buildは止めず、missingをfinding化するほうがadversarial review目的に合う。
- stdoutにreview approvalやnext gate commandを出さない。status、artifact path、known gap countだけ出す。
