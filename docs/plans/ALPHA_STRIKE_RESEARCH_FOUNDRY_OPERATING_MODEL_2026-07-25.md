<!--
作成日: 2026-07-25_00:52 JST
更新日: 2026-07-25_00:52 JST
-->

# Alpha Strike / Research Foundry Operating Model

## Status

```text
DOCUMENT_STATUS=PLAN_ONLY
IMPLEMENTATION_PERMISSION=false
CORE_INTEGRATION_PERMISSION=false
PAPER_PERMISSION=false
LIVE_PERMISSION=false
ACTUAL_CASH_PERMISSION=false
```

この文書は、利益探索と研究基盤開発の投資順序を固定する意思決定記録である。実装済み機能、alpha、profit proof、paper/live readinessを示さない。

## 結論

MarketLens Strikeのロードマップは、次の二つのゴールを同時に持つ。

1. **Alpha Strike**: 個人規模だから採算が合う、狭い・小容量・短命・運用が泥臭い可能性を含む利益仮説を、限定予算のCampaignとして現実へぶつける。
2. **Research Foundry**: 複数Campaignで実害として再発した判断・失敗・作業だけを再利用可能な能力へ昇格させ、次のAlpha Strikeの速度と命中率を改善する。

二つは直列ではない。

```text
Alpha Strike Campaign
        │
        ├─ 利益候補または正しいKill
        │
        └─ 再発した障害・判断・残差
                     ↓
             Research Foundry候補
                     │
                     ├─ Coreへ昇格
                     └─ Local hackのまま維持
```

Research Foundryの完成を待ってAlpha Strikeを始めてはならない。Foundry作業はCampaignを停止させず、同じCampaignのShadow評価として進める。

## 現在地

現行Repoはbacktest-first / venue-neutralのresearch and evidence workspaceであり、Crypto PerpとStrategy Idea Candidateのevidence quality向上が現在方向である。

実装済みの主要資産には、次がある。

- fail-closedなCandidate / Backtest / Kill / Human Review系Artifact
- Strategy Idea Seed Foundry A1の決定論的Technical SeedとGeneration Attempt Ledger
- NDXのdeterministic precheck、LLM review pack export、result import、exit gate
- Coreを変更しない`tools/backtest_spikes/`のDiscovery Spike前例

一方、次は未実装または未証明である。

- Research Orchestrator
- Research Policyの増分価値
- Archive / Resume / Hypothesis Portfolio
- actual cash profit
- tiny-live measurement
- production live order

したがって現在の限界投資先は、完成版Foundryではなく、実Campaignと同時に走らせる小さなResearch Policy A/B Discovery Spikeである。

## Goal A: Alpha Strike

### ゴール

限定した研究費、人間時間、Data範囲の中で、After-cost、Capacity、Executionを考慮した候補、または決定的なKillへ高速に到達する。

一般化、完全自動化、綺麗な共通基盤は完成条件に含めない。

### 許容する非対称リスク

- 一回限りの分析Script
- 特定Venue / Symbol / Time window専用の仮実装
- 手動Data整形
- 使い捨てPrompt
- 短命な仮説
- 小容量で機関には意味が薄い機会
- 結果が悪ければ破棄するSpike

### 許容しない省略

- Information cutoffと`available_at`
- Source path / hash
- 全TrialとRetry
- Cost model
- Look-ahead / leakage検査
- `NO_TRADE`比較
- Kill理由
- 事前のBudget / Success / Stop条件
- Paper / live / actual cash境界

原則は次である。

> コードは使い捨ててよい。証拠と試行履歴は使い捨てない。

### Campaignの最小契約

各Campaignは次を開始前に固定する。

```yaml
campaign_id:
research_question:
economic_mechanism:
individual_advantage:
decisive_uncertainty:
competing_explanations:
input_artifacts:
information_cutoff_at:
budget:
  human_minutes_cap:
  compute_minutes_cap:
  provider_cost_jpy_cap:
  max_branches:
success_condition:
kill_conditions:
forbidden_actions:
```

Budget値は普遍値を置かず、最初のCampaignの実測後に校正する。ただしBudget未設定のCampaignは開始しない。

### Alpha Strikeの成果

成果は候補数ではなく、次のいずれかである。

- After-costで検証継続価値がある候補
- 適用条件を明確に狭めた仮説
- 必要Data gapの特定
- 高価な実験を不要にした証拠
- 正しいKill

## Goal B: Research Foundry

### ゴール

Alpha Strikeで複数回実証された反復作業、見逃し、判断、失敗経路だけを再利用可能な能力へ変換し、同じ研究予算で得られる決定的結果を増やす。

自律度、Agent数、Artifact数、Schema数は成果ではない。

### Core昇格条件

Campaign内のLocal hackをFoundryへ昇格できるのは、次のいずれかを満たす場合だけとする。

1. 独立した二つ以上のCampaignで、同じ不足が実害として再発した。
2. Future leakage、Trial欠落、Boundary違反等の重大なCorrectness欠陥を防ぐ。
3. 次の少数Campaignで実装・保守費を回収できる合理的見込みがある。

`二つ以上`と`少数Campaign`は単発事例の一般化を抑える工学的初期値であり、統計的保証ではない。実績により改定する。

### 当面のFoundry候補

- Research Policy
- Evidence / Residual / Next Experimentの最小Contract
- Repeated Sampling比較
- Blind review
- Cost accounting
- Trial / Retry ledger
- Policy versionとInput hash

### 当面Coreへ入れないもの

- Multi-Agent supervisor
- Bandit / BOHB / MAP-Elites
- Full hypothesis graph
- Online fine-tuning
- 自動Policy更新
- Distributed queue
- Provider APIの自動実行
- A2全量Archive / Resume

## 非線形運用規則

### Rule 1: CampaignはFoundryを待たない

Research Policy A/B Spikeが未完了でも、現行の最良手段でAlpha Strike Campaignを進める。

### Rule 2: FoundryはShadowで測る

同じFrozen Evidenceを使い、現行方式、Repeated Sampling、Research Policy付き方式を比較する。Foundry候補はCampaignの判断を書き換えず、Shadow提案として評価する。

### Rule 3: Foundry予算は権利ではない

現Checkpointでは、Foundry関連作業のEngineering effort上限をAlpha Strike関連作業の20%程度とする。これは初期Ceilingであり、価値が実測されるまで増額しない。

### Rule 4: 勝った部分だけ昇格する

Research Policyが有効でも、Archive、Scheduler、Multi-Agentまで一括解禁しない。効果が確認された最小部品だけを別Checkpointで検討する。

### Rule 5: 手動方式を正式Baselineとして残す

人間がArtifactを読み、必要な追加指示を与える現行方式を削除しない。Foundryが勝てなければ現状維持へ戻す。

## 現Checkpoint

```text
CHECKPOINT_ID=RPAB-0
CHECKPOINT_GOAL=Research Policy A/B Discovery Spikeを実装・実行し、Repeated Sampling baselineに対する増分価値を判定する
```

現在許可するもの:

- 独立Spikeの計画と実装
- 既存Artifactのread-only取込み
- 手動Export / external model invocation / result import
- Blind human review
- Prospective experimentを一件だけ実行

現在許可しないもの:

- `src/`への統合
- Public CLI
- Candidate / Backtest decisionの書換え
- Paper / live / actual cash
- Provider API secretの追加
- Policyの自動更新
- A2以降のFoundry実装

## Checkpoint Decision

RPAB-0の終了Decisionは次のいずれかとする。

```text
PROMOTE_THIN_HARNESS
REVISE_POLICY_ONCE
KEEP_MANUAL_BASELINE
INCONCLUSIVE
INVALID_EXPERIMENT
```

`PROMOTE_THIN_HARNESS`は、次の限定Checkpointを検討する許可であり、Core統合やOrchestrator実装を自動許可しない。

## 重大な失敗経路

### Research theater

Proposalが詳しくなっただけで、実験、Kill、Data gap特定に接続しない。

停止条件:

- 次実験を実行できない
- 判断が変わらない
- 高価な無駄を防がない
- 文章量だけが増える

### Compute leakage

Policy側だけToken、Tool、時間が増え、改善をPolicy効果と誤認する。

対策:

- Repeated SamplingをBaselineにする
- Usageを保存する
- 同費用比較ができない場合はPareto比較にする

### Holdout汚染

Case結果を見てPolicyを修正し、同じCaseで再評価する。

対策:

- Policy freeze
- Archived diagnosticとProspective caseの分離
- 一度見たCaseを未知評価へ再利用しない

### Early-kill bias

Policyが常にKILL、または常にPIVOTへ偏る。

対策:

- 正しく停止すべきCaseを含める
- 人間が後から深掘りして失敗したCaseも含める
- RepairとRegressionを同時に測る

### Foundry capture

基盤BacklogがCampaignより大きくなる。

停止条件:

- Foundry作業がAlpha Strike作業のCeilingを超える
- 次Campaignで再利用されない
- Maintenanceが節約時間を上回る

## 事実・推論・仮定・未確認

### 事実

- 現行Repoにはfail-closed Artifact、LLM review pack、result import、独立Spikeの前例がある。
- Research OrchestratorとResearch Policyの増分価値は未証明である。
- actual cash profitとproduction liveは未証明である。

### 推論

- 現在はCore実装より、実CampaignとShadow Spikeの並行実施の方が機会損失を抑えられる。
- Foundryの要件は、実Campaignで再発した痛みから抽出する方が事前設計より信頼できる。

### 仮定

- 同じEvidence bundleで複数回のModel実行が可能である。
- 最低一件のArchived diagnostic caseと一件のCurrent / Prospective caseを用意できる。
- Blind human reviewを実施できる。

### 未確認

- 最初のAlpha Strike Campaignとして期待値が最も高い仮説。
- Model実行CostとSampling数の適正値。
- Research PolicyがRepeated Samplingに勝つか。
- Proposal品質改善が利益候補発見率へ転移するか。

## 次に行うこと

[Research Policy A/B Discovery Spike Implementation Plan](RESEARCH_POLICY_AB_DISCOVERY_SPIKE_IMPLEMENTATION_2026-07-25.md)に従い、独立Spikeだけを実装する。

実装と同時に、同じCaseを現行手動方式でも進める。SpikeはCampaignをBlockしない。
