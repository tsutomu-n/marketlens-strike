<!--
作成日: 2026-06-26_18:34 JST
更新日: 2026-06-26_18:34 JST
-->

# Pass 385: Live Evidence Report Artifact Path Extraction

## 目的

`src/sis/reports/live_evidence_report.py` の `build_live_evidence_report_data()` から、Live Evidence report artifact path 解決を独立モジュールへ切り出す。

この pass は、データ構築本体の見通しを改善し、artifact path の manifest override / default path / evidence card fallback を直接テストできるようにする。

## 対象

- `src/sis/reports/live_evidence_report.py`
- `src/sis/reports/live_evidence_report_artifacts.py`
- `tests/test_live_evidence_report_artifacts.py`

## 制約

- public CLI command 名・option は変えない。
- summary key 名、artifact key 名、Markdown / HTML report text・順序は変えない。
- schema、auth、DB、CI、dependency、paper/live safety boundary は変えない。
- `LiveEvidenceArtifacts` は既存 import 互換のため `sis.reports.live_evidence_report` から引き続き import できる状態を保つ。
- Pass 377-384 の未コミット変更は保持し、上書きしない。

## 実装方針

1. RED: `tests/test_live_evidence_report_artifacts.py` を追加し、まだ存在しない `sis.reports.live_evidence_report_artifacts` の import で失敗させる。
2. GREEN: `LiveEvidenceArtifacts` と `build_live_evidence_artifacts()` を新モジュールへ移す。
3. 既存の `live_evidence_report.py` は新 helper を呼ぶだけにし、`LiveEvidenceArtifacts` は re-export して互換を保つ。
4. 既存 report rendering、summary normalize、validation、quote diagnostics、row count、log tail 処理は触らない。

## 検証

- `CI=true timeout 120 uv run pytest -q tests/test_live_evidence_report_artifacts.py`
- `CI=true timeout 120 uv run pytest -q tests/test_live_evidence_report.py tests/test_live_evidence_report_inputs.py tests/test_live_evidence_report_tables.py`
- `CI=true timeout 120 uv run pytest -q tests/test_monitoring_comparison.py -k 'LiveEvidenceReportData or live_evidence'`
- `uv run ruff format src/sis/reports/live_evidence_report.py src/sis/reports/live_evidence_report_artifacts.py tests/test_live_evidence_report_artifacts.py`
- `uv run ruff check src/sis/reports/live_evidence_report.py src/sis/reports/live_evidence_report_artifacts.py tests/test_live_evidence_report_artifacts.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help`
- `git diff --check`
- `./scripts/check`

## リスクと対策

- import 互換リスク: `LiveEvidenceArtifacts` を元モジュールで明示 re-export する。
- default path 変更リスク: direct test で UTC date default と manifest override を固定する。
- evidence card fallback 変更リスク: helper には既存の fallback 結果を引数で渡し、探索ロジック自体は既存 input helper に残す。

## ロールバック

この pass の追加ファイルと `live_evidence_report.py` の helper 呼び出し変更だけを戻せばよい。生成物、依存関係、外部状態は変更しない。
