# 0722-PyBotters

## このノートの扱い

Pythonで取引所API/WebSocketに接続する実行・データ取得候補として扱う。売買戦略ではなく、接続層。

## 元ノートの要旨

PyBottersのClient、APIキー、WebSocket、DataStore、aiohttp引数、取引所接続例など。

## 今日時点での補正

PyBottersの価値は、取引所接続を薄く扱えること。一方、APIキー、WebSocket切断、rate limit、取引所仕様変更、再接続、注文冪等性を設計しないと危険。

## 理想的ナラティブ / 誤謬リスク

- `SECURITY_SECRET`: APIキー例をそのままdocsやコードに置く危険。
- `EXECUTION_GAP`: API接続できることと安全に注文できることを混同する。
- `OPERATIONAL_COMPLEXITY`: 非同期処理と再接続のバグ。

## 戦略部品への分解

- `Data Collector`: WebSocket market data。
- `Execution Adapter`: REST注文、cancel、position取得。
- `Monitoring Layer`: reconnect、heartbeat、latency。
- `Security Guard`: secret管理、権限最小化、ログマスク。

## 実験に落とすなら

最初はprivate APIを使わず、public WebSocketの受信、再接続、DataStore更新を記録する。次にread-only private、最後にpaper/sandbox相当へ進む。

## 採用条件

切断、再接続、重複イベント、APIエラー時に状態が壊れないこと。

## 捨て条件

注文ID、再試行、キャンセル、ポジション同期を管理できない場合。

## 現在性チェック

PyBotters公式docs/GitHub、対応取引所、Pythonバージョン、取引所API変更を確認する。

## 関連 docs

- `../STRATEGY_PARTS_CATALOG.md`

## 原ノート

- `../obsidian_note_copies/05_execution_and_stack/0722-PyBotters.md`

