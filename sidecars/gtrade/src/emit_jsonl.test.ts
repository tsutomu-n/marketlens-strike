import { expect, test } from "bun:test";
import { buildSidecarLine, extractPair } from "./emit_jsonl.js";
import type { TargetPair } from "./registry.js";

const spyTarget: TargetPair = {
  canonicalSymbol: "SPY",
  venueSymbol: "SPY/USD",
  pairIndex: 86,
  assetClass: "index"
};

const rawLiveShape = {
  pairs: Array.from({ length: 91 }, () => null),
  pairInfos: {
    "86": { onePercentDepthAboveUsd: "123000000", onePercentDepthBelowUsd: "456000000" }
  },
  fees: Array.from({ length: 14 }, () => null),
  groups: Array.from({ length: 7 }, () => null),
  isForexOpen: true,
  isStocksOpen: false,
  isIndicesOpen: false,
  isCommoditiesOpen: true
};

rawLiveShape.pairs[86] = {
  from: "SPY",
  to: "USD",
  spreadP: "200000000",
  groupIndex: "5",
  feeIndex: "5"
};
rawLiveShape.pairs[87] = {
  from: "QQQ",
  to: "USD",
  spreadP: "200000000",
  groupIndex: "5",
  feeIndex: "5"
};
rawLiveShape.pairs[90] = {
  from: "XAU",
  to: "USD",
  spreadP: "0",
  groupIndex: "6",
  feeIndex: "13"
};
rawLiveShape.fees[5] = {
  totalPositionSizeFeeP: "500000000",
  minPositionSizeUsd: "2500000"
};
rawLiveShape.fees[13] = {
  totalPositionSizeFeeP: "350000000",
  minPositionSizeUsd: "800000"
};
rawLiveShape.groups[5] = {
  name: "indices",
  minLeverage: "1100",
  maxLeverage: "100000"
};
rawLiveShape.groups[6] = {
  name: "commodities-1",
  minLeverage: "2000",
  maxLeverage: "250000"
};

test("extractPair uses the current live raw trading-variables shape", () => {
  const transformedWithoutPairs = {
    globalTradingVariables: {},
    pairIndexes: {},
    blockNumber: 123
  };

  expect(extractPair(spyTarget, transformedWithoutPairs, rawLiveShape)).toMatchObject({
    canonical_symbol: "SPY",
    venue_symbol: "SPY/USD",
    pair_index: 86,
    asset_class: "index",
    pair_from: "SPY",
    pair_to: "USD",
    spreadP_raw: "200000000",
    spread_bps: 2,
    fee_index: "5",
    group_index: "5",
    group_name: "indices",
    max_leverage: "100000",
    total_position_size_fee_p: "500000000",
    min_position_size_usd: "2500000",
    one_percent_depth_above_usd: "123000000",
    one_percent_depth_below_usd: "456000000"
  });
});

test("buildSidecarLine emits all configured targets from raw payload", () => {
  const line = buildSidecarLine({
    tsClient: "2026-05-22T00:00:00.000Z",
    network: "arbitrum",
    backendUrl: "https://backend-arbitrum.gains.trade",
    raw: rawLiveShape,
    transformed: { globalTradingVariables: {}, pairIndexes: {} }
  });

  expect(line).toMatchObject({
    venue: "gtrade",
    network: "arbitrum",
    market_status: {
      isIndicesOpen: false,
      isCommoditiesOpen: true
    }
  });
  expect(line.raw_payload_sha256).toBeString();
  expect(line.pairs).toBeArrayOfSize(3);
  expect((line.pairs as Record<string, unknown>[])[2]).toMatchObject({
    canonical_symbol: "XAU",
    spreadP_raw: "0",
    spread_bps: 0,
    fee_index: "13",
    group_name: "commodities-1"
  });
});
