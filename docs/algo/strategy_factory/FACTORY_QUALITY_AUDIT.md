# Factory Quality Audit

`strategy_factory/` に対する抜け漏れ・割愛・誤謬リスクの監査メモです。

## 修正した弱点

| weakness | fix |
|---|---|
| gate条件が粗い | `GATE_REVIEW_CHECKLIST.md` を追加 |
| 重複候補の増殖を止める資料がない | `DUPLICATE_CONTROL.md` を追加 |
| candidate sheetに証跡欄が弱い | evidence、review、promotion blocker欄を追加 |
| backlogが次の作業を示すには粗い | evidence、blocker、last_review列を追加 |
| reject taxonomyが実装/運用寄りの失敗を一部拾えていない | `PROMOTION` と `OPS` 系コードを追加 |

## まだ残るリスク

- docsだけでは候補台帳の整合性を自動検査できない。
- backlog tableは手動更新なので、重複keyやstatus遷移ミスが起こり得る。
- scoreは人間の判断を含むため、過信しない。
- 初期候補 `SIG-001` から `SIG-007` は実装済み戦略ではない。

## 合格条件

- 新候補は必ずcandidate sheetから始まる。
- backlogへ載せる前にduplicate keyを確認する。
- 次gateへ進める時は `GATE_REVIEW_CHECKLIST.md` を使う。
- rejectはtaxonomy codeで残す。
- Crypto/DeFi固有候補を通常シグナル候補と混ぜない。

## Better Next

将来、docsだけで不足した場合は、次をコード化する。

- candidate sheetのschema validation。
- duplicate keyの自動検査。
- backlog status遷移の検査。
- reject codeの存在検査。
- evidence pathの存在検査。
