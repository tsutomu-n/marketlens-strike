import { expect, test } from "bun:test";
import { parsePricingPayload } from "./pricing_parser.js";

test("parsePricingPayload parses v4-style m/i/t payload", () => {
  const parsed = parsePricingPayload({
    t: 1779457500000,
    prices: {
      "86": { m: "512.34", i: "512.31" },
      "87": { m: 443.21, i: 443.2 },
      "90": { m: "2365.12", i: "2365.15" },
    },
  });

  expect(parsed.oracle_ts_ms).toBe(1779457500000);
  expect(parsed.points).toContainEqual({
    pair_index: 86,
    mark_price: 512.34,
    index_price: 512.31,
    mark_index_inferred_equal: false,
  });
  expect(parsed.points).toContainEqual({
    pair_index: 90,
    mark_price: 2365.12,
    index_price: 2365.15,
    mark_index_inferred_equal: false,
  });
});

test("parsePricingPayload supports m/i array fallback", () => {
  const parsed = parsePricingPayload({
    t: 1779457500000,
    m: [null, null, 100, 101],
    i: [null, null, 99, 100],
  });

  expect(parsed.points.find((point) => point.pair_index === 2)).toEqual({
    pair_index: 2,
    mark_price: 100,
    index_price: 99,
    mark_index_inferred_equal: false,
  });
});

test("parsePricingPayload supports flat pairIndex/price array payload", () => {
  const parsed = parsePricingPayload([372, 0.08619989, 86, 746.2425, 90, 2365.12]);

  expect(parsed.oracle_ts_ms).toBeNull();
  expect(parsed.points).toContainEqual({
    pair_index: 86,
    mark_price: 746.2425,
    index_price: 746.2425,
    mark_index_inferred_equal: true,
  });
  expect(parsed.points).toContainEqual({
    pair_index: 90,
    mark_price: 2365.12,
    index_price: 2365.12,
    mark_index_inferred_equal: true,
  });
});
