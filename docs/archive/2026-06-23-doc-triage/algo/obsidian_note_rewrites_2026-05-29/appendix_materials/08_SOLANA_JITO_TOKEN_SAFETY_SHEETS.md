<!--
作成日: 2026-05-29_21:42 JST
更新日: 2026-06-05_08:11 JST
-->

# Solana, Jito, Token Safety Sheets

Solana/Meme token/Jito系ノートを、自動購入ではなく安全観測と除外条件へ変換する資料です。

## 1. Observer-first Flow

```text
Token Discovery
  -> Token Metadata / Mint Inspection
  -> Token Safety Filter
  -> Sellability Simulation
  -> Paper Observation
  -> Manual Review
  -> Small Canary Only If Approved
```

禁止:

```text
Token Discovery -> Auto Buy
```

## 2. Token Safety Checklist

| check | unsafe / review |
|---|---|
| mint authority | 追加発行可能ならreview/unsafe |
| freeze authority | 凍結可能ならunsafe寄り |
| token extensions | transfer fee等の売買コストを確認 |
| holder concentration | 上位holder集中ならreview |
| LP / pool depth | 薄いならunsafe |
| sell simulation | 売れないならunsafe |
| pool age | 生成直後はobserveのみ |
| metadata mutability | 後から変えられるならreview |

出力は次に限定する。

```text
safe_to_observe
needs_manual_review
unsafe
```

`safe_to_observe` は `safe_to_buy` ではない。

## 3. Sellability Sheet

| item | record |
|---|---|
| token | |
| pool | |
| expected sell route | |
| simulation result | pass/fail |
| expected output | |
| slippage setting | |
| fail reason | |
| decision | observe/review/unsafe |

## 4. Jito Observation Sheet

Jitoは収益源ではなく、execution qualityの観測対象として扱う。

| metric | reason |
|---|---|
| submitted count | 送信数 |
| landed count | 着地数 |
| failed count | 失敗数 |
| tip paid | 費用 |
| latency | 遅延 |
| route comparison | standard txとの差 |
| failed reason | blockhash, simulation, leader, slot境界等 |
| uncled/reorg-like risk note | landed扱いの確認 |

比較:

```text
standard tx route
Jito route with tip
```

合格条件:

- tip込みでもexecution qualityが改善する。
- failure reasonが記録できる。
- failed/unknown時に新規行動を止められる。

## 5. Bot Boundary

Bot化前に必要:

```text
manual approval
fund cap
kill switch
read-only/paper window
sellability check
position state recovery
unknown order stop
secret not in repo/docs
```

Bot化不可:

```text
private key前提のノートをそのまま実装
auto buyが最初の機能
sell simulationなし
LP/holder/mint/freeze未確認
failed txの扱いなし
```
