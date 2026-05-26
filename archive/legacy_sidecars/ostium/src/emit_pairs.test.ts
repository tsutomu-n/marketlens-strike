import { expect, test } from "bun:test";
import { buildPairsLine, normalizePair } from "./emit_pairs.js";

test("normalizePair preserves fee, OI, leverage, and market fields", () => {
  expect(
    normalizePair({
      pairId: "12",
      pairFrom: "US500",
      pairTo: "USD",
      category: "indices",
      maxLeverage: 200,
      overnightMaxLeverage: 50,
      rolloverFeePerBlock: "123",
      rolloverRate: { long: "0.01", short: "-0.02" },
      openInterest: "1000",
      buyOpenInterest: "600",
      sellOpenInterest: "400",
      maxOpenInterest: "5000",
      midPx: "6000",
      askPx: "6001",
      bidPx: "5999",
      isMarketOpen: true,
      isDayTradingClosed: false,
      secondsToToggleIsDayTradingClosed: 120
    })
  ).toMatchObject({
    pair_id: "12",
    venue_symbol: "US500-USD",
    max_leverage: 200,
    overnight_max_leverage: 50,
    rollover_rate_long: "0.01",
    open_interest: "1000",
    max_open_interest: "5000",
    is_market_open: true
  });
});

test("buildPairsLine emits sidecar metadata envelope", () => {
  const line = buildPairsLine({
    tsClient: "2026-05-22T00:00:00.000Z",
    pairs: [{ pairId: "1", pairFrom: "XAU", pairTo: "USD" }]
  });

  expect(line.venue).toBe("ostium");
  expect(line.raw_payload_sha256).toBeString();
  expect(line.pairs).toBeArrayOfSize(1);
});

