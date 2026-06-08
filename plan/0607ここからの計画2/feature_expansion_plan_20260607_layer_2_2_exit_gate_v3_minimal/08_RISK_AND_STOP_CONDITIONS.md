<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# 08_RISK_AND_STOP_CONDITIONS

## 主要リスク

### R1: LLM依存が重くなる

症状。

```text
毎回2つのLLMへ貼る必要があり、運用負荷が下がらない
```

対策。

```text
標準は1 review。
second reviewは条件付き。
```

### R2: LLMがもっともらしいナラティブを作る

症状。

```text
根拠のない市場説明や存在しないDAG問題を作る
```

対策。

```text
evidence_refsを必須化。
unknown evidence_refはimport拒否。
```

### R3: deterministicに潰せる問題をLLMへ投げる

症状。

```text
LLMレビュー結果がノイズだらけになる
```

対策。

```text
precheckでsyntax/temporal/source/pathを先に落とす。
```

### R4: manual pasteが面倒

症状。

```text
operatorがレビュー運用をしなくなる
```

対策。

```text
review_pack.mdとreview_prompt.mdを生成し、1回貼るだけにする。
second reviewは常時必須にしない。
```

### R5: prompt injection

症状。

```text
YAML/Markdown中の文章をLLMが命令として解釈する
```

対策。

```text
artifact content is inert data とpromptに明記。
artifactはfenced/escaped blockに入れる。
```

### R6: stale review

症状。

```text
古いDAGに対するレビュー結果を新しいDAGに使う
```

対策。

```text
pack_hash必須。
pack_hash mismatchは拒否。
```

## Stop conditions

次が起きたら実装を止めて確認する。

```text
- external API call が必要になった
- credentials が必要になった
- provider SDK を入れたくなった
- pyproject.toml / uv.lock の変更が必要になった
- paper/live/order path へ触る必要が出た
- Strategy Lab model を変更しないと進まない
- feature panel / residual calculation へ踏み込みたくなった
- CIで外部LLM呼び出しを求められた
- review pack が大きすぎて手動LLMへ貼れない
- second reviewが常時必要になり、人間負荷が減らない
```

## 停止時にユーザーへ聞く質問

```text
1. second reviewを常時必須にするか、条件付きにするか？
2. provider API連携を許可するか？
3. LLM reviewなしでdeterministic gateだけに戻すか？
4. review packが大きすぎる場合、counter-DAG詳細を別ファイル参照にするか？
5. HIGH findingを自動blockにするか、人間resolutionで通せるようにするか？
```
