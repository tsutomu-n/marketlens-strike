<!--
作成日: 2026-06-15_21:47 JST
更新日: 2026-06-16_06:46 JST
-->

# Backtest Docs Code-Truth Audit

## 結論

コード、schema、CLI、lockfile、現行 artifact summary を正にすると、`docs/backtest/` は次の4分類で整理するのがよい。

1. **更新できるドキュメント**: 現行入口として残し、少し直せば current doc として使える。
2. **古い内容があるドキュメント**: 価値はあるが、古い数値、古い future/plan 表現、実装済みを未実装扱いする記述が混ざる。
3. **作り直したほうがいいドキュメント**: 目的は有用だが、計画・実装結果・履歴・現在値が混ざり、差分修正より再構成した方が安全。
4. **削除・アーカイブしてもよいドキュメント**: current truth ではなく、過去の判断ログやサンプルとしてだけ価値がある。

現時点で operator に読ませる正本は、`README.md`、`BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md`、`OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md`、`BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md` の4本に寄せるのが現実的である。

2026-06-16_06:46 JST に、この audit に基づいて current 導線を整理した。古い計画・採用前調査・固定 sample は `docs/archive/backtest/` に移し、現行コードを正とする [BACKTEST_CURRENT_TECHNICAL_REFERENCE.md](BACKTEST_CURRENT_TECHNICAL_REFERENCE.md) と、大学生向け current-only guide の [BACKTEST_CAPABILITY_UNIVERSITY_GUIDE_2026-06-16.md](BACKTEST_CAPABILITY_UNIVERSITY_GUIDE_2026-06-16.md) を追加した。

## 照合したコード上の事実

2026-06-15_21:47 JST 時点で確認した事実:

- `uv run sis --help` は `strategy-backtest-framework-run`、`strategy-backtest-microstructure-readiness`、`strategy-backtest-qstrader-contract`、`strategy-backtest-portfolio-validation-contract`、`strategy-backtest-pybroker-contract`、`strategy-backtest-constraint-breaker-decision` を公開している。
- `src/sis/backtest/pack_contract.py` は `BacktestArtifactKey.FRAMEWORK_RUN` と `BacktestArtifactKey.FRAMEWORK_RUN_REPORT` を持つ。
- `src/sis/backtest/pack_runner.py` は `strategy-backtest-pack` の chain 内で framework run matrix を生成し、pack manifest に入れる。
- `src/sis/backtest/artifact_summary.py` と `src/sis/backtest/artifact_summary_registry.py` は `framework_run` summary を読む。
- `schemas/strategy_backtest_adapter_spike.v1.schema.json` と `src/sis/backtest/frameworks.py` は `hftbacktest` を reference-only candidate として扱う。
- `pyproject.toml` / `uv.lock` の optional extras は `vectorbt`, `bt`, `metrics`, `reports`。
- 通常 env の current artifact summary は `framework_run.summary.executed_count=0`, `framework_run.summary.skipped_count=4`, `pack_validation.decision=PASS`, `pack_validation.check_count=206`, `no_lookahead_diff.summary.coverage_status=runtime_replay_verified`, `no_lookahead_diff.summary.false_negative_risk=low`。
- `uv run python scripts/check_current_docs.py` は `126 current docs` の metadata / links / EOF / legacy roots を pass した。ただしこの checker は本文の意味的鮮度までは保証しない。

## 更新できるドキュメント

これらは current docs として残す価値が高い。小さな表現修正や数値の非固定化で運用できる。

| Document | 判定 | 理由 | 必要な更新 |
|---|---|---|---|
| `docs/backtest/README.md` | 更新して維持 | backtest docs の入口。CLI surface と新 command の説明が概ね現行コードと合っている | `CURRENT_*` や古い計画 docs への誘導を「historical / design context」と明示する |
| `docs/backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md` | 更新して維持 | operator 向けの現行機能説明として最も使いやすい | artifact summary の数値を固定値ではなく確認 command ベースに寄せ続ける |
| `docs/backtest/OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md` | 更新して維持 | 実行手順として有用。`framework_run` と reference-only contract も反映済み | optional extras 実行後は pack を同 env で再実行する注意を維持する |
| `docs/backtest/BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md` | 更新して維持 | live / wallet / signing / dependency adoption の境界を守る文書として重要 | reference-only artifact と dependency adoption の違いをさらに冒頭で強調する |
| `docs/backtest/OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md` | 更新して維持 | 実装済み計画の根拠として価値がある | 「実装前に確認した事実」節に、実装後は古い箇所があることを明示する |
| `docs/backtest/BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md` | 更新して維持 | 責務分離の完了記録として有用 | `pack_contract.py` と summary registry に `framework_run` が入った事後補正を足す |
| `docs/backtest/VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md` | 更新して維持 | `vectorbt` 採用根拠として必要 | 最新機能説明ではなく license decision memo として固定する |
| `docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md` | 更新して維持 | Trade[XYZ] 専用 Python API surface の説明として current scope が明確 | Strategy Authoring 標準 backtest とは別 surface である旨を現行 README と合わせる |

## 古い内容があるドキュメント

これらは残してよいが、そのまま current truth として読ませると誤読リスクがある。

| Document | 古い内容 | コード上の現在値 | 推奨処置 |
|---|---|---|---|
| `docs/archive/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md` | 本文前半に「次に作るべき scope」「hftbacktest はまだ持たない」など、実装前の記述が残る | `hftbacktest` は reference-only candidate 済み。framework matrix は pack / comparison / summary に統合済み | archive 済み。current 技術正本は `BACKTEST_CURRENT_TECHNICAL_REFERENCE.md` |
| `docs/archive/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md` | 2026-06-14 時点の completion artifact 前提が中心。新5 command は末尾補正のみ | CLI は新 command を公開済み | archive 済み。current 技術正本は `BACKTEST_CURRENT_TECHNICAL_REFERENCE.md` |
| `docs/archive/backtest/BACKTEST_CAPABILITY_BEFORE_AFTER_UNIVERSITY_GUIDE_2026-06-15.md` | 「実装完了後」という未来形が残る | 通常レーンは実装済み | archive 済み。current-only 版は `BACKTEST_CAPABILITY_UNIVERSITY_GUIDE_2026-06-16.md` |
| `docs/backtest/BACKTEST_HIGH_SCHOOL_GUIDE_2026-06-15.md` | 新しい `framework_run`、reference-only contract、constraint breaker の説明が薄い | CLI と docs は追加済み | 高校生向け current guide として軽く追記する |
| `docs/archive/backtest/BACKTEST_PLACEHOLDER_OUTPUT_SAMPLE_2026-06-15.md` | `check_count=198` が固定で載る | current summary は `pack_validation.check_count=206` | archive 済み |
| `docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md` | `check_count=198` が固定で載る | current summary は `206` | current artifact 値を再生成して更新、または `example at time of capture` と明記 |
| `docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md` | 「整理する計画」色が強い | backtest pack 自体は拡張済み。paper bridge は別問題 | paper observation docs 側と突き合わせて、完了/未完了を再判定する |
| `docs/backtest/OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md` | qstrader は runner contract 未設計としている | `strategy-backtest-qstrader-contract` は実装済み。ただし dependency / engine は未採用 | qstrader 行だけ現行 contract 実装済みに更新 |
| `docs/archive/backtest/OSS_BACKTEST_FRAMEWORK_EVALUATION_PLAN_2026-06-13.md` | 採用前評価と一時 smoke の表現が中心 | `vectorbt`, `bt`, `metrics`, `reports` は optional extra 済み | archive 済み |
| `docs/archive/backtest/METRICS_REPORT_OPTIONAL_EXTRAS_DECISION_2026-06-13.md` | `bt` の位置付けや framework matrix 統合前の説明が中心 | framework matrix が pack / summary に統合済み | archive 済み。current execution は guide を読む |
| `docs/archive/backtest/VECTORBT_ADOPTION_PLAN_2026-06-13.md` | Phase 0 など採用前段階の記述が長い | `vectorbt==1.0.0` は optional extra 済み | archive 済み。license 正本は `VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md` |

## 作り直したほうがいいドキュメント

これらは差分修正だけだと読み手が「現在」「計画」「履歴」を混同しやすい。

| Document | 作り直す理由 | 作り直し後の形 |
|---|---|---|
| `docs/archive/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md` | 700行超で、current detail、過去 smoke、採用判断、実装前 scope、実装後補正が同居している | archive 済み。current 技術正本は `BACKTEST_CURRENT_TECHNICAL_REFERENCE.md` |
| `docs/archive/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md` | 外部 framework 役割表として有用だが、実装前 plan と実装後補正が混ざる | archive 済み。current 技術正本は `BACKTEST_CURRENT_TECHNICAL_REFERENCE.md` |
| `docs/archive/backtest/BACKTEST_CAPABILITY_BEFORE_AFTER_UNIVERSITY_GUIDE_2026-06-15.md` | 実装前後比較としては役目を終えた。現在は「完了後」が現状 | archive 済み。current-only 版は `BACKTEST_CAPABILITY_UNIVERSITY_GUIDE_2026-06-16.md` |
| `docs/archive/backtest/BACKTEST_PLACEHOLDER_OUTPUT_SAMPLE_2026-06-15.md` | placeholder sample と current artifact sample の境界が弱く、固定数値がすぐ古くなる | archive 済み |
| `docs/archive/backtest/BACKTEST_SYSTEM_COMPLETION_PLAN_2026-06-14.md` | completion plan は完了済み計画としての価値はあるが、current operator doc ではない | archive 済み |

## 削除・アーカイブしてもよいドキュメント

削除より archive 推奨。過去の判断根拠としては価値があるが、current docs の主導線から外すべきもの。

| Document | 推奨 | 理由 |
|---|---|---|
| `docs/archive/backtest/BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md` | archived | 初期 pivot 計画。現在は Strategy Authoring backtest と pack が実装済みで、operator 入口としては古い |
| `docs/archive/backtest/BACKTEST_SYSTEM_COMPLETION_PLAN_2026-06-14.md` | archived | completion plan。完了済みなら current guide ではなく履歴 |
| `docs/archive/backtest/OSS_BACKTEST_FRAMEWORK_EVALUATION_PLAN_2026-06-13.md` | archived | 採用前評価計画。現在は optional extras と reference-only contract が実装済み |
| `docs/archive/backtest/VECTORBT_ADOPTION_PLAN_2026-06-13.md` | archived | 採用計画としては完了済み。license decision memo があれば current には不要 |
| `docs/archive/backtest/BACKTEST_PLACEHOLDER_OUTPUT_SAMPLE_2026-06-15.md` | archived | placeholder / fixed sample は current artifact とズレやすい |
| `docs/archive/backtest/METRICS_REPORT_OPTIONAL_EXTRAS_DECISION_2026-06-13.md` | archived | decision memo としては残せるが、current execution guide ではない |

## 残すべき主導線

README からの主導線は次に絞るとよい。

1. `BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md`: 利用者向け。
2. `OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md`: 実行手順。
3. `BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md`: 禁止事項と future scope。
4. `OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md`: 実装済み通常レーンと Constraint Breaker。
5. `VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md`: vectorbt license / owner approval。
6. `TRADE_XYZ_PURE_BACKTEST_V0_1.md`: Trade[XYZ] 専用 API surface。

## 次にやる更新タスク

優先順:

1. 完了: `README.md` のリンク説明を `current`, `supporting`, `archive` に分けた。
2. 完了: `BACKTEST_PLACEHOLDER_OUTPUT_SAMPLE_2026-06-15.md` は `docs/archive/backtest/` に移した。
3. 完了: `CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md` と `CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md` は archive した。
4. 完了: `BACKTEST_CAPABILITY_BEFORE_AFTER_UNIVERSITY_GUIDE_2026-06-15.md` は archive し、`BACKTEST_CAPABILITY_UNIVERSITY_GUIDE_2026-06-16.md` を追加した。
5. 完了: archive 移動後に README と current docs のリンクを更新した。

## 誤謬リスク

- `check_current_docs.py` が通ることは、リンクと metadata が壊れていないことを示すだけで、本文が current truth であることは示さない。
- `data/research/*` の artifact 値は runtime state であり、optional extras env と通常 env で `framework_run.executed_count` が変わる。
- 古い計画文書は削除すると意思決定の履歴を失う。削除より archive が安全。
- `CURRENT_` という名前のまま古い計画や補正メモを持つ文書は、最も誤読されやすい。
