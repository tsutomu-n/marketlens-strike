# 1202-JitoとSolana

## このノートの扱い

Jito Bundlesを利益機会として見るのではなく、Solana実行・MEV・atomicity・latencyの制約理解として扱う。

## 元ノートの要旨

Jito Bundles、Block Engine、Searcher、tip、leader schedule、bundle失敗、atomicな複数transaction、低遅延環境など。

## 今日時点での補正

Jitoは実行品質を改善し得るが、同時に競争が激しい領域。一般的な戦略準備では、bundleを使って勝つことより、失敗時の扱い、チップ、slot境界、simulation、秘密鍵管理を理解することが重要。

## 理想的ナラティブ / 誤謬リスク

- `MEV_LATENCY_ARMS_RACE`: block engine近接やtipで優位に立てるという前提。
- `EXECUTION_GAP`: bundleが想定通り全て成功する前提。
- `SECURITY_SECRET`: keypair、block engine API、payerの扱い。
- `OPERATIONAL_COMPLEXITY`: 実行層が複雑になり、戦略検証が曖昧になる。

## 戦略部品への分解

- `Execution Adapter`: bundle送信、simulation、retry、tip。
- `Risk Guard`: slot boundary、bundle failure、partial assumptionの排除。
- `Security Guard`: keypair隔離、payer制限、ログマスク。
- `Monitoring Layer`: landed/not landed、latency、tip cost。

## 実験に落とすなら

まずmainnet資金を使わず、bundle lifecycleと失敗理由の観測だけを行う。戦略評価では、tipと失敗率をコストとして入れる。

## 採用条件

Jitoを使うことで期待値が改善する理由が、単なる速度ではなく、失敗率・slippage・atomicityで説明できること。

## 捨て条件

tipやインフラ費用を入れると期待値が消える場合。

## 現在性チェック

Jito公式docs、Block Engine API、Searcher client、tip account、Solana runtime仕様を確認する。

## 関連 docs

- `../STRATEGY_PARTS_CATALOG.md`

## 原ノート

- `../obsidian_note_copies/04_market_specific/1202-JitoとSolana.md`

