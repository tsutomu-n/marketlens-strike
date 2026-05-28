# 1129-Solanaトレーディングボット

## このノートの扱い

botをそのまま使う資料ではなく、Solana token botの危険点と安全ゲートを作るための資料として扱う。

## 元ノートの要旨

Solana上でtokenを自動購入/売却するbotの設定、private key、RPC、WebSocket、スナイプリスト、フィルタ、Warp/Jito実行、利益確定、損切りなど。

## 今日時点での補正

未知tokenの自動購入は、技術的に動いても戦略としては非常に危険。まずはpaper observation、token safety検査、wallet隔離、資金上限、手動承認を前提にする。

## 理想的ナラティブ / 誤謬リスク

- `DANGEROUS_AUTOMATION`: 条件に合うtokenを自動購入すれば機会を取れるという前提。
- `SECURITY_SECRET`: private key、RPC、wallet、設定ファイルの漏洩。
- `MEV_LATENCY_ARMS_RACE`: Warp/Jitoで速度問題を解決できるという前提。
- `EXECUTION_GAP`: 利確/損切りが低流動性tokenで機能する前提。

## 戦略部品への分解

- `Token Safety Filter`: mint/freeze authority、LP、metadata、holder集中、transfer fee。
- `Security Guard`: 空wallet、資金上限、secret隔離、ログマスク。
- `Execution Adapter`: simulation、priority fee、slippage、retry制御。
- `Risk Guard`: paper-only、manual approval、kill switch。

## 実験に落とすなら

最初は購入しない。新規tokenを検出し、フィルタ結果、流動性、価格推移、売却可能性だけを記録する。

## 採用条件

token safety判定と売却可能性が、取引前に機械的に確認できること。

## 捨て条件

private keyを設定ファイルに置く、未知tokenを自動購入する、資金上限がない、売却テストがない場合。

## 現在性チェック

対象botリポジトリの更新状況、依存関係、Solana RPC仕様、Warp/Jitoの現行仕様を確認する。

## 関連 docs

- `../STRATEGY_BLUEPRINTS.md`
- `../NARRATIVE_RISK_REGISTER.md`

## 原ノート

- `../obsidian_note_copies/04_market_specific/1129-Solanaトレーディングボット.md`

