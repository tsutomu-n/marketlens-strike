import { expect, test } from "bun:test";
import { buildPositionsLine, normalizePosition } from "./emit_positions.js";

const pairPosition = {
  position: {
    pairId: "12",
    pairFrom: "XAU",
    pairTo: "USD",
    pid: "99",
    idx: 0,
    side: "B",
    szi: "1",
    entryPx: "2400",
    leverage: "10",
    ntl: "24000",
    unrealizedPnl: "12",
    returnOnEquity: "0.01",
    liquidationPx: "2200",
    collateralUsed: "2400",
    cumRollover: "-1.2",
    openTimestamp: 1779415479000,
    isDayTrade: false,
    maxLeverage: "100",
    maxWithdrawable: "1200"
  }
} as const;

test("normalizePosition preserves liquidation reference fields", () => {
  expect(normalizePosition(pairPosition)).toMatchObject({
    pair_id: "12",
    venue_symbol: "XAU-USD",
    side: "long",
    entry_px: "2400",
    liquidation_px: "2200",
    cumulative_rollover_usd: "-1.2"
  });
});

test("buildPositionsLine emits read-only open positions envelope", () => {
  const line = buildPositionsLine({
    tsClient: "2026-05-22T00:00:00.000Z",
    user: "0xabc",
    response: {
      pairPositions: [pairPosition],
      marginSummary: { accountValue: "1000" },
      time: 1779415479000
    }
  });

  expect(line.venue).toBe("ostium");
  expect(line.position_count).toBe(1);
  expect(line.raw_payload_sha256).toBeString();
});
