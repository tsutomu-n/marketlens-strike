# Why Not StateStrike Factory

StateStrike風のStrategy Factoryをそのまま入れない理由:

```text
- marketlens-strikeは既にTrade[XYZ] / paper / ops / micro live safetyが太い
- 大きなFactoryを入れると既存の安全surfaceを壊しやすい
- 今必要なのは実行基盤ではなく研究・評価・候補生成基盤
- research層にStrategy Research Labを足す方が責務が明確
```
