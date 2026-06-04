<!--
作成日: 2026-06-01_14:13 JST
更新日: 2026-06-05_07:57 JST
-->

# Trade[XYZ] Docs Code-Truth Audit

この文書は、現在のコードと生成済みartifactを正として、Trade[XYZ]実データ収集と純粋バックテスト周辺のドキュメントを分類する。

## 現在のコード正本

```text
収集対象設定:
  configs/trade_xyz_data_collection.yaml

設定loader:
  src/sis/venues/trade_xyz/collection_config.py

収集CLI:
  src/sis/commands/quotes.py

長時間wrapper:
  scripts/collect_trade_xyz_data_cycle.sh
  scripts/collect_trade_xyz_data_until_ready.sh

readiness/status:
  src/sis/venues/trade_xyz/readiness.py
  src/sis/venues/trade_xyz/collection_status.py

現在status:
  data/ops/trade_xyz_collection_status.json
  data/reports/trade_xyz_collection_status.md
```

## 重要な現在ルール

```text
2026-05-30以前の実データ:
  使用禁止。
  data/archive/pre_2026_05_31_unusable_real_data/ に移動済み。

収集対象symbol / interval:
  コードやshell scriptへ直書きしない。
  configs/trade_xyz_data_collection.yaml から読む。

secret / credential:
  YAMLへ入れない。
  環境変数またはCLI引数で渡す。

完了判定:
  uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
  が exit 0 になるまで未完了。
```

## 更新できるドキュメント

| Path | 判定 | 更新内容 |
|---|---|---|
| `docs/OPERATIONS_RUNBOOK.md` | 更新済み | collection config、5/30以前archive、env override境界を追記済み |
| `docs/集めるべき実データ0531-2108/README.md` | 更新済み | wrapper envをconfig参照に修正、5/30以前使用禁止を追記済み |
| `docs/TRADE_XYZ_REAL_DATA_COLLECTION_STATUS_APPENDIX_2026-06-01.md` | 新規作成済み | 現在status、未充足、archive、設定正本を記録 |
| `docs/CODE_STATUS.md` | 更新候補 | Trade[XYZ]実データ収集の正本が `configs/trade_xyz_data_collection.yaml` へ移ったことを短く追記するとよい |
| `.ai_memory/HANDOFF.md` | 更新候補 | 次のhandoff時に5/30以前archiveとcollection configを反映する |

## 古い内容があるドキュメント

| Path | 古い理由 | 扱い |
|---|---|---|
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` | 5/28時点の監査で、現在のcollection config、5/30以前archive、readiness状態を反映していない | historical auditとして残す。current docsとして読む場合は注意書きが必要 |
| `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md` | 収集コマンド例が古く、5/30以前データ使用禁止とconfig正本を反映していない | archive候補または冒頭にhistorical扱いを明記 |
| `plan/TRADE_XYZ_BACKTEST_V0_1_1_REAL_DATA_STABILIZATION_PLAN_REV4.md` | REV5以降と実装後のコードに追い越されている | 背景資料として残す |
| `plan/TRADE_XYZ_BACKTEST_V0_1_2_REAL_DATA_HARDENING_PLAN_REV5.md` | 実装計画としては有用だが、現在のarchive/config実装後の運用正本ではない | 背景資料として残す。運用手順の正本にはしない |

## 作り直したほうがいいドキュメント

| Path | 理由 | 推奨 |
|---|---|---|
| `docs/集めるべき実データ0531-2108/README.md` | 長大で、実データ定義、運用runbook、設計思想、phase planが混在している | `real_data_contract.md`, `collection_runbook.md`, `readiness_gate.md`, `known_gaps.md` に分割 |
| `docs/OPERATIONS_RUNBOOK.md` | 全体runbookにTrade[XYZ]実データ収集の詳細が増えている | Trade[XYZ]実データ収集だけを `docs/trade_xyz/REAL_DATA_COLLECTION_RUNBOOK.md` に分離し、ここからリンク |
| `docs/CODE_STATUS.md` | migration全体のstatusと現在の実データ収集statusが混ざり始めている | code statusは実装面に限定し、runtime/data readinessは別docへ分離 |

## 削除・アーカイブしてもよいドキュメント

削除は推奨しない。現在のRepoでは、監査履歴やplan履歴としての価値が残るため、必要なら `docs/archive/` または `plan/archive/` へ移す。

| Path | 推奨 |
|---|---|
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` | `docs/archive/` へ移動候補 |
| `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md` | `docs/archive/` へ移動候補 |
| `plan/TRADE_XYZ_BACKTEST_V0_1_1_REAL_DATA_STABILIZATION_PLAN_REV4.md` | `plan/archive/` へ移動候補 |

## 現在のreadinessへの影響

5/30以前のデータをarchiveしたため、古いsignal/real-market artifactに依存したpass判定は消えた。再取得後の現在statusは以下。

```text
backtest_data_ready: false
readiness_decision: NOT_READY
failing_requirements:
  - quote_coverage
known_gap_requirements:
  - oracle_timestamp_provenance
pass_requirements:
  - real_market_reference
  - account_specific_fee
signal_candles: pass
funding_events: pass
```

real market reference と account-specific fee は現在の readiness manifest では pass である。残る fail は quote coverage、known gap は oracle timestamp provenance である。

## 次に更新するなら

1. `docs/CODE_STATUS.md` に collection config と5/30以前archiveを短く追記する。
2. `docs/OPERATIONS_RUNBOOK.md` からTrade[XYZ]実データ収集の詳細を専用runbookへ分離する。
3. 5/30以前使用禁止を checker で機械検査したい場合は、`scripts/check_current_docs.py` ではなく data artifact用の別checkerを作る。
