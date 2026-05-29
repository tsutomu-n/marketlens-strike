# 05 Symbol Binding Contract

## Why This Exists

Trade[XYZ]で執行するsymbolと、real marketで正データとして見るsymbolは一致しない場合がある。

例:

```text
execution_symbol = XYZ100
real_market_symbol = QQQ

execution_symbol = SP500
real_market_symbol = SPY

execution_symbol = NVDA
real_market_symbol = NVDA
```

この分離をしないと、`QQQ` signalをそのまま `XYZ100` の注文候補へ流す事故が起きる。

## Required Model

```python
class SymbolBinding(BaseModel):
    execution_venue: Literal["trade_xyz"]
    execution_symbol: str
    real_market_symbol: str
    asset_class: str
    country: str | None = None
    currency: str = "USD"
```

## Required Rules

```text
- StrategySignalRecordには execution_symbol と real_market_symbol を必ず持たせる
- TradeCandidateにも両方を持たせる
- PaperCandidatePackにも両方を残す
- PaperIntentPreviewにも両方を残す
- canonical_symbolだけに依存しない
```

## Examples

```yaml
symbol_bindings:
  - execution_venue: trade_xyz
    execution_symbol: SP500
    real_market_symbol: SPY
    asset_class: index
    currency: USD

  - execution_venue: trade_xyz
    execution_symbol: XYZ100
    real_market_symbol: QQQ
    asset_class: basket_index
    currency: USD

  - execution_venue: trade_xyz
    execution_symbol: NVDA
    real_market_symbol: NVDA
    asset_class: equity
    currency: USD
```

## Tests

```text
- XYZ100 requires real_market_symbol=QQQ or explicit configured proxy
- SP500 requires real_market_symbol=SPY or explicit configured proxy
- execution_symbol missing => fail
- real_market_symbol missing => fail
- strategy signal cannot be produced without SymbolBinding
```
