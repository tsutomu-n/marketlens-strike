<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# 09_OPEN_QUESTIONS

## 実装前に決めなくてもよい質問

```text
- どのLLM providerを使うか
- API連携するか
- VXNをいつ使うか
- NQ futuresをいつ取り込むか
- 2.3 feature panelをどう作るか
```

これらは今回の実装範囲外。

## 実装前に決めるべき質問

### Q1. second reviewを常時必須にするか？

決定。

```text
常時必須にしない。
標準は1 review。
条件付きでsecond adversarial reviewを要求する。
```

### Q2. prompt_hashを必須にするか？

決定。

```text
manual運用ではpack_hash必須、prompt_contract_version必須。
prompt_hashはあれば検証する。
API運用を後で入れる場合はprompt_hash必須化を検討する。
```

理由。

```text
manual pasteではprompt_hashの厳密運用が摩擦になる。
pack_hashが主要なstale review防止になる。
```

### Q3. HIGH findingを自動blockにするか？

決定。

```text
HIGHは自動REVISEではなく、人間resolutionで通せる。
BLOCKERは通せない。
```

ただし、同じtarget/categoryでHIGHが複数出る場合はREVISE推奨。

### Q4. REJECT_SEEDはLLMだけで確定するか？

決定。

```text
LLMだけでは確定しない。
REJECT_SEEDには human resolution または explicit operator flag が必要。
```

### Q5. reportをdocsへ置くかdataへ置くか？

決定。

```text
runtime report:
  data/reports/

operator doc:
  docs/research/ndx/09_LLM_REVIEW_GATE.md
```
