<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# D_DESIGN_REVIEW_FINDINGS

## 追加調査後の修正判断

### 1. 二段LLMレビューは常時必須にしない

v2ではconstructive/adversarialの二段レビューを強く推奨していたが、運用負荷が高い。

v3では以下へ修正。

```text
標準:
  1 review

追加:
  second adversarial review は条件付き
```

### 2. pack_hashは必須、prompt_hashは緩和

manual paste運用ではprompt_hashが摩擦になりやすい。したがって、

```text
pack_hash:
  必須

prompt_contract_version:
  必須

prompt_hash:
  optional
```

API modeを将来入れる場合はprompt_hash必須に戻す。

### 3. deterministic precheckを厚くする

LLMに回す前に、コードで落とすべきものを増やす。

```text
- DAG acyclic
- temporal matrix
- source tier integrity
- evidence catalog completeness
- scope exclusion scan
- pack size guard
- prompt injection sanitization
```

### 4. Counter-DAGは本数ではなくカテゴリ

最低カテゴリ。

```text
broad_market
rates
semiconductor_or_mega_cap
vol_regime
etf_tracking_noise
futures_price_discovery
index_methodology
selection_or_temporal_data_quality
```

optional。

```text
macro_event
calendar_opex
options_gamma
```

### 5. LLMは承認者ではない

LLMの役割は `finding extractor`。

```text
LLM:
  risk extraction

code:
  final gate decision

human:
  only unresolved/high-risk decisions
```

### 6. API連携は後回し

初版はmanual paste運用のみ。OpenAI/Anthropic/Grok APIをrepoへ入れない。

理由。

```text
- API keyが必要
- 依存が増える
- CIが不安定になる
- provider lock-inが起きる
```
