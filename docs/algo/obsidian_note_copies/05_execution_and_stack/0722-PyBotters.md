

# pybotters: 仮想通貨botterのための高度なAPIクライアント

![pybotters logo](https://raw.githubusercontent.com/pybotters/pybotters/main/docs/logo_150.png)


## 📌 概要

`pybotters`は、[仮想通貨 botter (crypto bot traders)](https://medium.com/perpdex/botter-the-crypto-bot-trader-in-japan-2f5f2a65856f)のためのPythonライブラリです。このプロジェクトは日本語で開発されています。

このライブラリは**HTTPとWebSocket APIクライアント**であり、トレーディングボット開発に有用な以下の機能を提供します。

## 🚀 特徴

- ✨ HTTP / WebSocketクライアント
    - プライベートAPIの**自動認証**
    - WebSocketの**自動再接続**と**自動ハートビート**
    - [`aiohttp`](https://docs.aiohttp.org/)ベースのクライアント
- ✨ DataStore
    - WebSocketメッセージデータハンドラー
    - オーダーブック更新などの**差分データの処理**
    - **高速データ処理**とクエリ
- ✨ その他の特徴
    - 型ヒントのサポート
    - [`asyncio`](https://docs.python.org/ja/3/library/asyncio.html)を使用した非同期プログラミング
    - Discordコミュニティ

## 🏦 対応取引所

| 取引所名 | API認証 | DataStore | 取引所APIドキュメント |
| --- | --- | --- | --- |
| bitFlyer | ✅ | ✅ | [リンク](https://lightning.bitflyer.com/docs) |
| GMO Coin | ✅ | ✅ | [リンク](https://api.coin.z.com/docs/) |
| bitbank | ✅ | ✅ | [リンク](https://github.com/bitbankinc/bitbank-api-docs) |
| Coincheck | ✅ | ✅ | [リンク](https://coincheck.com/ja/documents/exchange/api) |
| Bybit | ✅ | ✅ | [リンク](https://bybit-exchange.github.io/docs/v5/intro) |
| Binance | ✅ | ✅ | [リンク](https://binance-docs.github.io/apidocs/spot/en/) |
| OKX | ✅ | ✅ | [リンク](https://www.okx.com/docs-v5/en/) |
| Phemex | ✅ | ✅ | [リンク](https://phemex-docs.github.io/) |
| Bitget | ✅ | ✅ | [リンク](https://bitgetlimited.github.io/apidoc/en/mix/) |
| MEXC | ✅ | サポートなし | [リンク](https://mexcdevelop.github.io/apidocs/spot_v3_en/) |
| KuCoin | ✅ | ✅ | [リンク](https://www.kucoin.com/docs/beginners/introduction) |
| BitMEX | ✅ | ✅ | [リンク](https://www.bitmex.com/app/apiOverview) |

## 🐍 必要条件

Python 3.8以上

## 🔧 インストール方法

[PyPI](https://pypi.org/project/pybotters/)からインストール（安定版）:

```sh
pip install pybotters
```

[GitHub](https://github.com/pybotters/pybotters)からインストール（最新版）:

```sh
pip install git+https://github.com/pybotters/pybotters.git
```

## 📝 使用方法

bitFlyer APIの使用例:

### HTTP API

バージョン1.0からの新インターフェース: **Fetch API**

より簡単なリクエスト/レスポンス処理:

```python
import asyncio

import pybotters

apis = {
    "bitflyer": ["YOUER_BITFLYER_API_KEY", "YOUER_BITFLYER_API_SECRET"],
}


async def main():
    async with pybotters.Client(
        apis=apis, base_url="https://api.bitflyer.com"
    ) as client:
        # 残高の取得
        r = await client.fetch("GET", "/v1/me/getbalance")

        print(r.response.status, r.response.reason, r.response.url)
        print(r.data)

        # 注文の作成
        CREATE_ORDER = False  # 注文を作成する場合は `True` に設定してください。
        if CREATE_ORDER:
            r = await client.fetch(
                "POST",
                "/v1/me/sendchildorder",
                data={
                    "product_code": "BTC_JPY",
                    "child_order_type": "MARKET",
                    "side": "BUY",
                    "size": 0.001,
                },
            )

            print(r.response.status, r.response.reason, r.response.url)
            print(r.data)


asyncio.run(main())
```

aiohttpベースのAPI:

```python
import asyncio

import pybotters

apis = {
    "bitflyer": ["YOUER_BITFLYER_API_KEY", "YOUER_BITFLYER_API_SECRET"],
}


async def main():
    async with pybotters.Client(
        apis=apis, base_url="https://api.bitflyer.com"
    ) as client:
        # 残高の取得
        async with client.get("/v1/me/getbalance") as resp:
            data = await resp.json()

        print(resp.status, resp.reason)
        print(data)

        # 注文の作成
        CREATE_ORDER = False  # 注文を作成する場合は `True` に設定してください。
        if CREATE_ORDER:
            async with client.post(
                "/v1/me/sendchildorder",
                data={
                    "product_code": "BTC_JPY",
                    "child_order_type": "MARKET",
                    "side": "BUY",
                    "size": 0.001,
                },
            ) as resp:
                data = await resp.json()

            print(data)


asyncio.run(main())
```

### WebSocket API

```python
import asyncio

import pybotters


async def main():
    async with pybotters.Client() as client:
        # キューの作成
        wsqueue = pybotters.WebSocketQueue()

        # WebSocketに接続し、Tickerをサブスクライブ
        await client.ws_connect(
            "wss://ws.lightstream.bitflyer.com/json-rpc",
            send_json={
                "method": "subscribe",
                "params": {"channel": "lightning_ticker_BTC_JPY"},
            },
            hdlr_json=wsqueue.onmessage,
        )

        # メッセージの反復処理 (Ctrl+Cで中断)
        async for msg in wsqueue:
            print(msg)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
```

### DataStore

```python
import asyncio

import pybotters


async def main():
    async with pybotters.Client() as client:
        # DataStoreの作成
        store = pybotters.bitFlyerDataStore()

        # WebSocketに接続し、板情報をサブスクライブ
        await client.ws_connect(
            "wss://ws.lightstream.bitflyer.com/json-rpc",
            send_json=[
                {
                    "method": "subscribe",
                    "params": {"channel": "lightning_board_snapshot_BTC_JPY"},
                },
                {
                    "method": "subscribe",
                    "params": {"channel": "lightning_board_BTC_JPY"},
                },
            ],
            hdlr_json=store.onmessage,
        )

        # 板の最良価格を監視 (Ctrl+Cで中断)
        with store.board.watch() as stream:
            async for change in stream:
                board = store.board.sorted(limit=2)
                print(board)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
```

## 📖 ドキュメンテーション

🔗 https://pybotters.readthedocs.io/ja/stable/ (日本語)

## 🗽 ライセンス

MIT

## 💖 作者

スポンサーになってください！:

[![GitHub Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-%23db61a2.svg?&logo=github&logoColor=181717&&style=flat-square&labelColor=white)](https://github.com/sponsors/MtkN1)

X (旧Twitter):

[![X (formerly Twitter) Follow](https://img.shields.io/twitter/follow/MtkN1XBt)](https://twitter.com/MtkN1XBt)

Discord:

[![Discord Widget](https://discord.com/api/guilds/832651305155297331/widget.png?style=banner3)](https://discord.com/invite/CxuWSX9U69)



# 機能解説

# pybotters: 詳細ガイドと高度な使用方法

## 目次
1. [Client クラス](#client-クラス)
2. [HTTP API](#http-api)
3. [Base URL](#base-url)
4. [WebSocket API](#websocket-api)
5. [認証](#認証)
6. [DataStore](#datastore)
7. [取引所固有の DataStore](#取引所固有の-datastore)
8. [WebSocketQueue](#websocketqueue)
9. [aiohttp との違い](#aiohttp-との違い)
10. [高度な使用方法](#高度な使用方法)

## Client クラス

`pybotters.Client` は HTTP リクエストを行うためのメインクラスです。使用開始には以下のステップが必要です：

1. `asyncio` と `pybotters` をインポート
2. 非同期関数を `async def` で定義
3. 定義した非同期関数内で `async with` ブロックを使用して `Client` インスタンスを初期化

```python
import asyncio
import pybotters

async def main():
    async with pybotters.Client() as client:
        ...

asyncio.run(main())
```

## HTTP API

### Fetch API

`Client.fetch()` メソッドを使用して HTTP リクエストを作成します。

```python
async def main():
    async with pybotters.Client() as client:
        result = await client.fetch(
            "GET",
            "https://api.bitflyer.com/v1/getticker",
            params={"product_code": "BTC_JPY"},
        )
        print(result.response.status, result.response.reason)
        print(result.data)
```

### HTTP method API

従来の HTTP メソッド API も利用可能です：

```python
async def main():
    async with pybotters.Client() as client:
        async with client.get(
            "https://api.bitflyer.com/v1/getticker",
            params={"product_code": "BTC_JPY"},
        ) as resp:
            data = await resp.json()
        print(data)
```

## Base URL

`Client` の `base_url` 引数を設定することで、取引所 API エンドポイントのベース URL を省略できます：

```python
async def main():
    async with pybotters.Client(base_url="https://api.bitflyer.com") as client:
        r = await client.fetch("GET", "/v1/getticker")
        r = await client.fetch("GET", "/v1/getboard")

        # WebSocket API の URL には base_url は適用されません
        await client.ws_connect("wss://ws.lightstream.bitflyer.com/json-rpc")
```

## WebSocket API

`Client.ws_connect()` メソッドで WebSocket 接続を作成します：

```python
async def main():
    async with pybotters.Client() as client:
        ws = await client.ws_connect(
            "wss://ws.lightstream.bitflyer.com/json-rpc",
            send_json={
                "method": "subscribe",
                "params": {"channel": "lightning_ticker_BTC_JPY"},
            },
            hdlr_json=lambda msg, ws: print(msg),
        )
        await ws.wait()  # Ctrl+C to break
```

## 認証

`Client` クラスの `apis` 引数に API 認証情報を渡すことで、認証処理が自動的に行われます：

```python
async def main():
    apis = {
        "bitflyer": ["BITFLYER_API_KEY", "BITFLYER_API_SECRET"],
    }
    async with pybotters.Client(apis=apis) as client:
        result = await client.fetch("GET", "https://api.bitflyer.com/v1/me/getbalance")
        print(result.data)
```

## DataStore

DataStore を利用することで WebSocket からのデータを簡単に処理、参照できます：

```python
ds = pybotters.DataStore(
    keys=["id"],
    data=[
        {"id": 1, "data": "foo"},
        {"id": 2, "data": "bar"},
        {"id": 3, "data": "baz"},
        {"id": 4, "data": "foo"},
    ],
)
print(ds.get({"id": 1}))
print(ds.find({"data": "foo"}))
```

## 取引所固有の DataStore

取引所固有の DataStore は対応取引所における WebSocket チャンネルの DataStore 実装です：

```python
async def main():
    async with pybotters.Client() as client:
        store = pybotters.bitFlyerDataStore()

        await client.ws_connect(
            "wss://ws.lightstream.bitflyer.com/json-rpc",
            send_json={
                "method": "subscribe",
                "params": {"channel": "lightning_ticker_BTC_JPY"},
                "id": 1,
            },
            hdlr_json=store.onmessage,
        )

        while True:  # Ctrl+C to break
            ticker = store.ticker.get({"product_code": "BTC_JPY"})
            print(ticker)

            await store.ticker.wait()
```

## WebSocketQueue

DataStore が実装されていない取引所や、自らの実装でデータを処理したい場合は `WebSocketQueue` を利用できます：

```python
async def main():
    async with pybotters.Client() as client:
        wsqueue = pybotters.WebSocketQueue()

        await client.ws_connect(
            "wss://ws.lightstream.bitflyer.com/json-rpc",
            send_json={
                "method": "subscribe",
                "params": {"channel": "lightning_ticker_BTC_JPY"},
            },
            hdlr_json=wsqueue.onmessage,
        )

        async for msg in wsqueue:  # Ctrl+C to break
            print(msg)
```

## aiohttp との違い

pybotters は aiohttp を基盤として利用していますが、いくつかの重要な違いがあります：

- pybotters は HTTP リクエストの自動認証機能により、自動的に HTTP ヘッダーなどを編集します。
- POST リクエストなどのデータは引数 `data` に渡します。aiohttp の `json` 引数は pybotters では許可されません。
- `Client.fetch()` は pybotters 独自の API です。
- `Client.ws_connect()` は pybotters 独自の実装になっており、再接続機能や認証機能を搭載しています。

## 高度な使用方法

### `apis` の暗黙的な読み込み

`Client` の `apis` 引数を指定せずに、以下の方法で暗黙的に読み込むことができます：

1. カレントディレクトリに `apis.json` を配置する
2. 環境変数 `PYBOTTERS_APIS` にファイルパスを設定する

優先順位は以下の通りです：

1. `Client` の引数 `apis` を明示的に指定
2. カレントディレクトリの `apis.json`
3. 環境変数 `PYBOTTERS_APIS` の JSON ファイル

### 認証の無効化

自動認証処理を無効にする場合は、リクエストメソッドの引数 `auth=None` を設定します：

```python
async def main():
    apis = {"some_exchange": ["KEY", "SECRET"]}
    async with pybotters.Client(apis=apis) as client:
        r = await client.fetch("GET", "/public/endpoint", auth=None)
```

### Fetch データの検証

`FetchResult.data` は JSON をパースしたオブジェクトが格納されますが、`if` 文で評価しておくことでコードの安全性が高まります：

```python
async def main():
    async with pybotters.Client() as client:
        r = await client.fetch("GET", "https://google.com")  # Not JSON content

        if r.data:  # NotJSONContent
            print(r["data"])  # KeyError will be raised
        else:
            print(f"Not JSON content: {r.text[:50]} ... {r.text[-50:]}")
```

### aiohttp のキーワード引数

`Client` とリクエストメソッドのキーワード引数 `**kwargs` に対応する引数を渡すことで、aiohttp の引数にバイパスできます：

```python
async def main():
    async with pybotters.Client() as client:
        # TimeoutError will be raised
        await client.fetch("GET", "https://httpbin.org/delay/10", timeout=3.0)
```

### 複数の WebSocket 送信者/ハンドラ

`Client.ws_connect()` の `send_*` 引数と `hdlr_*` 引数にリスト形式で渡すことで、複数のメッセージ送信や受信メッセージの複数ハンドリングができます：

```python
async def main():
    async with pybotters.Client() as client:
        ws = await client.ws_connect(
            "ws://...",
            send_json=[
                {"op": "subscribe", "channel": "ch1"},
                {"op": "subscribe", "channel": "ch2"},
                {"op": "subscribe", "channel": "ch3"},
            ],
            hdlr_json=[
                func1,
                func2,
                func3,
            ],
        )
        await ws.wait()
```

### 現在の WebSocket 接続

`WebSocketApp.current_ws` プロパティから aiohttp の WebSocket クラスにアクセスでき、1回限りの WebSocket メッセージ送信などができます：

```python
async def main():
    async with pybotters.Client() as client:
        ws = await client.ws_connect("ws://...")

        if ws.current_ws:
            await ws.current_ws.send_json({"channel": "order"})

        await ws.wait()
```

### WebSocket ハートビート

`Client.ws_connect()` の引数 `heartbeat` で自動 WebSocket ハートビートの設定を変更できます：

```python
async def main():
    async with pybotters.Client() as client:
        ws = await client.ws_connect("ws://...", heartbeat=10.0)  # default value
```

手動でハートビートを実行することもできます：

```python
async def main():
    async with pybotters.Client() as client:
        ws = await client.ws_connect("ws://...")

        while True:
            await ws.heartbeat()

            ...  # Trading strategy
```

### WebSocket 再接続のバックオフ

`Client.ws_connect()` の引数 `backoff` で再接続の指数バックオフを変更できます：

```python
async def main():
    async with pybotters.Client() as client:
        ws = await client.ws_connect("ws://...", backoff=(1.92, 60.0, 1.618, 5.0))  # default value
```

### WebSocket 再接続時の URL

`WebSocketApp.url` に URL を代入することで、接続する WebSocket URL を変更できます：

```python
async def main():
    async with pybotters.Client() as client:
        ws = await client.ws_connect("ws://example.com/ws?token=xxxxx")
        ...
        ws.url = "ws://example.com/ws?token=yyyyy"
```

### DataStore のイテレーション

DataStore はイテレーションによってデータを取得することもできます：

```python
ds = pybotters.DataStore(
    keys=["id"],
    data=[
        {"id": 1, "data": "foo"},
        {"id": 2, "data": "bar"},
        {"id": 3, "data": "baz"},
        {"id": 4, "data": "foo"},
    ],
)
for item in ds:
    print(item)

for item in reversed(ds):
    print(item)
```

### DataStore の最大データ数

DataStore は `DataStore._MAXLEN` 変数にて最大件数の制限を設けています：

```python
store = pybotters.bitFlyerDataStore()
print(store.ticker._MAXLEN)
print(store.executions._MAXLEN)
```

これらの高度な使用方法を活用することで、pybotters をより効果的に利用し、複雑なトレーディングボットを構築することができます。