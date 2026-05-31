結論：**アップロードされた現Repo情報を反映して、設計ZIPをRev2に更新しました。**
前回の設計から重要な修正があります。現Repoでは、すでに `src/sis/backtest/engine/**` と `tests/backtest/**` がかなり進んでおり、**「v0.1を作る」段階ではなく、「v0.1を壊さずCLI公開・RS戦略・funding/maker/L2へ拡張する」段階**です。

作成物：

* [Repo反映版 設計Handoff ZIP Rev2](/home/tn/projects/marketlens-strike/資料/RSライン/trade_xyz_backtest_next_design_handoff_repo_aware_20260531.zip)


## 確認した現Repo状態

アップロードZIP内の情報では：

```text
branch: main
commit: 6645688519c72eefedc963b1be1e98d7c05a9221
git status: clean
tests/backtest: 66 passed
```

注意点として、あなたの指定は `feature/backtest-engine-roadmap` でしたが、今回のZIPは **mainブランチ由来** です。
コーダーが実装する前に、`feature/backtest-engine-roadmap` にこの進捗が入っているか確認が必要です。

## Rev2で修正した要点

* **CLI公開**：まだ未実装。`src/sis/commands/backtest.py` を新設する計画に変更。
* **Parquet artifact writer**：すでに概ね実装済み。再実装ではなく contract hardening に変更。
* **RS新高値戦略**：未実装。`rs_features.py` / `rs_strategy.py` を追加対象に整理。
* **XYZ100/SP500レジーム判定**：未実装。`regime.py` を追加対象に整理。
* **funding interval厳密計算**：v0 placeholderあり。推測計算禁止、厳密化PRとして分離。
* **maker / post-only / queue model**：未実装。L2 replayなしに楽観実装しない方針。
* **L2 replay**：collector/normalizerはあるが、replay engineは未実装。
* **MT5 / IC Markets / CFD**：現Repoには入れず、別プロジェクト境界のみ文書化。

## ZIP内の主な中身

```text
docs/
  00_repo_current_state.md
  01_final_decision.md
  02_phase_plan_rev2.md
  03_feature_tasks_rev2.md
  04_target_files_rev2.md
  05_test_plan_rev2.md
  06_done_criteria_rev2.md
  07_risk_register.md
  08_current_repo_info_request.md

appendix/
  A_artifact_schema_drafts.md
  B_cli_command_spec.md
  C_rs_regime_feature_spec.md
  D_funding_maker_l2_spec.md
  E_future_mt5_icmarkets_cfd_boundary.md
  F_machine_readable_backlog_rev2.yaml

scripts/
  collect_current_repo_context_v2.sh
```

## いまのRepo情報は十分か

今回の設計更新には十分です。
ただし、実装レビューまでやるなら追加でほしいのは以下です。

```text
pyproject.toml
uv.lock
scripts/run_trade_xyz_backtest_smoke.py
scripts/check または Makefile / justfile
tests/test_backtest_bridge.py
tests/test_backtest_fixed_horizon.py
```

理由は、現Repoの `tests/backtest/test_real_quotes_smoke.py` が `scripts/run_trade_xyz_backtest_smoke.py` を参照している一方、今回ZIPには `scripts/` が含まれていなかったためです。CLI公開時に、既存scriptを残すのか、正式CLIへ寄せるのかを決める必要があります。

21:11:51.(05/31)
