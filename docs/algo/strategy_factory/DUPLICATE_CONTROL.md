<!--
作成日: 2026-05-30_07:44 JST
更新日: 2026-06-05_08:11 JST
-->

# Duplicate Control

戦略候補を量産すると、似たsignalが増えて管理不能になります。この資料は、重複候補を統合または棄却するための基準です。

## 1. Duplicate Key

候補には必ず `duplicate_key` を付ける。

```text
<archetype>:<universe>:<timeframe>:<trigger-family>
```

例:

```text
pullback:liquid-major:4h:ma-pullback
breakout:liquid-major:1h:range-retest
mean-reversion:liquid-major:1h:zscore-range
```

## 2. Same Candidate

次が同じなら、原則として同一候補です。

- archetype
- universe
- timeframe
- trigger family
- invalidation type
- baseline

処理:

- 新候補は `DUP_SIMILAR_SIGNAL` でarchive。
- 既存候補のnotesに差分だけ追記。

## 3. Variant Candidate

次だけが違うものは、別戦略ではなくvariantとして扱う。

- threshold
- MA period
- ATR period
- score weight
- no-trade threshold

処理:

- 同じcandidate sheet内の `parameter_neighborhood` に入れる。
- 新しいbacklog行を作らない。

## 4. New Candidate

次が違う場合だけ、新候補として扱う。

- signal archetypeが違う。
- invalidationの考え方が違う。
- baselineが違う。
- required inputsが構造的に違う。
- failure modeが違う。

## 5. Portfolio-level Duplicate

signal単体は違っても、損益挙動が同じなら量産価値は低い。

確認するもの:

- returns correlation
- drawdown timing
- shared failure regime
- same no-trade conditions
- same data dependency

同じ壊れ方をする候補は、別名でも分散にならない。

## 6. Archive Record

```md
# Duplicate Archive

- candidate:
- duplicate_of:
- duplicate_key:
- reason_code: DUP_SIMILAR_SIGNAL | DUP_SAME_ARCHETYPE_INPUTS | DUP_SUPERSEDED
- difference:
- retained_candidate:
```
