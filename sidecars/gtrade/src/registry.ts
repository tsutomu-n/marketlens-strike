export type TargetPair = {
  canonicalSymbol: "SPY" | "QQQ" | "XAU";
  venueSymbol: string;
  pairIndex: number;
  assetClass: "index" | "commodity";
};

export const TARGET_PAIRS: TargetPair[] = [
  { canonicalSymbol: "SPY", venueSymbol: "SPY/USD", pairIndex: 86, assetClass: "index" },
  { canonicalSymbol: "QQQ", venueSymbol: "QQQ/USD", pairIndex: 87, assetClass: "index" },
  { canonicalSymbol: "XAU", venueSymbol: "XAU/USD", pairIndex: 90, assetClass: "commodity" }
];

