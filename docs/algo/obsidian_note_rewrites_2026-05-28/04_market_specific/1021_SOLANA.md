# 1021_SOLANA

## このノートの扱い

Solanaプログラム開発例の索引としてではなく、Solana取引botを触る前に必要な基礎理解と危険領域の整理として扱う。

## 元ノートの要旨

Solana program examplesのREADME抜粋。Anchor、Native Rust、TypeScript、Python、token、PDA、CPI、Token Extensions、AMM、oracleなどの例が並ぶ。

## 今日時点での補正

多くの取引用途では独自on-chain programを作る必要はない。まず既存プログラム、トークン仕様、アカウント、署名、権限、rent、Token Extensionsのリスクを理解する方が重要。

## 理想的ナラティブ / 誤謬リスク

- `OPERATIONAL_COMPLEXITY`: on-chain programを作れば優位性が出るという前提。
- `SECURITY_SECRET`: wallet署名と権限管理の失敗リスク。
- `DANGEROUS_AUTOMATION`: botが未知トークンと直接やり取りする危険。

## 戦略部品への分解

- `Token Safety Filter`: mint authority、freeze authority、metadata、transfer fee。
- `Execution Adapter`: transaction、account、signature、commitment。
- `Security Guard`: wallet隔離、権限、dry-run、simulation。
- `Research Assistant`: 公式exampleで仕様を確認する。

## 実験に落とすなら

取引botではなく、mainnetに触れないローカル/テスト環境で、token account、mint、transfer、simulationの理解から始める。

## 採用条件

botが触るトークン仕様と権限を機械的に検査できること。

## 捨て条件

未知のprogramやtoken拡張を、人間の確認なしに取引対象にする場合。

## 現在性チェック

Solana公式Developer docs、solana-developers/program-examples、Anchor、Token Extensionsの現行仕様を確認する。

## 関連 docs

- `../STRATEGY_BLUEPRINTS.md`

## 原ノート

- `../obsidian_note_copies/04_market_specific/1021_SOLANA.md`

