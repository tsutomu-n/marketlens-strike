# Source Coverage Audit

今回の再構成対象は `../obsidian_note_copies/` にコピー済みの実ノート24本です。

## 対象外だが戦略準備上の抜け

`../SOURCE_NOTES_INDEX.md` には、未コピーだが高優先のノートが残っています。これらは今後の追加調査候補ですが、今回の再構成には含めません。

優先度が高いもの:

- `0906_モンテカルロ.md`: 検証の頑健性に直結する。
- `1101_時系列予測.md`: 予測モデル系ノートの補強に使える。
- `0710-APIs.md`: データ取得と取引所接続の棚卸しに使える。
- `1201-Self-Hosted Bot Protection.md`: bot防御と運用安全に使える。
- `1202-SolVal Guardian (SG).md`: Solana token safetyの補助になり得る。

## コピー除外またはマスク必須

APIキー、秘密鍵、2FA、recovery code、外部サービス接続情報を含む可能性のあるノートは、ここには再構成しません。将来扱う場合は、secret scanとマスク処理を先に行います。

## 防御目的のみ

sniper、rug、凍結解除、危険なbot運用に寄るノートは、戦略化せず、除外条件、危険検知、token safety、運用停止条件の設計に限定します。

