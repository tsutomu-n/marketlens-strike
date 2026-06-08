<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# 09 Open Questions

## 実装前に未解決なら危険な質問

### Q1. CLIはPhase Bで必須か

推奨判断:

```text
Phase AはCLIなし。
Phase Bの最後に validate/export の2コマンドだけ追加。
```

もしCLI追加が大きくなるなら、Python API + testsだけで止める。

### Q2. docs/research/ndx を current docs checker 対象にするか

推奨判断:

```text
最初は対象にしなくてもよい。
ただし作成するMarkdownにはmetadata headerを付ける。
```

チームが current docs として扱うなら `scripts/check_current_docs.py` の allowlist に追加する。

### Q3. `src/sis/research/hypothesis/` と `src/sis/research/dag/` の切り分け

推奨判断:

```text
hypothesis:
  Seed / mechanism / variable inventory / roles / temporal availability

dag:
  Core DAG contract / loader / validator / linter / export
```

この切り分けで進める。

## 後回し可能な質問

### Q4. VXNのデータ取得元

後回し。Phase A/Bでは `optional_provider_dependent` として登録するだけ。

### Q5. NQ futuresのデータ取得元

後回し。Phase A/Bでは `deferred` として登録するだけ。

### Q6. SOX直接取得かSMH代替か

初期計画では SMH を default proxy、SOX を optional proxy にする。

### Q7. Nasdaq methodology events をどこまで計算するか

Phase A/Bでは mechanism part / counter-DAG として登録するだけ。計算しない。

### Q8. Numerai式neutralizationをいつ入れるか

Phase C以降。今回入れない。

### Q9. DoWhy / causal-learn / PCMCI をいつ入れるか

Phase C以降。初期2.2ではDAG artifactとlinterを優先する。
