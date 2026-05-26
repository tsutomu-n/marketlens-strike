import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { OstiumClient } from "@ostium/builder-sdk";
import { sha256Json } from "./hash.js";

const outDir = process.env.OSTIUM_OUT_DIR ?? "../../data/raw/sidecar/ostium";

function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

export type PairLike = {
  pairId?: string | number;
  pairFrom?: string;
  pairTo?: string;
  category?: string;
  maxLeverage?: number;
  overnightMaxLeverage?: number;
  rolloverFeePerBlock?: string;
  openInterest?: string;
  buyOpenInterest?: string;
  sellOpenInterest?: string;
  maxOpenInterest?: string;
  rolloverRate?: { long?: string; short?: string };
  midPx?: string;
  askPx?: string;
  bidPx?: string;
  isMarketOpen?: boolean;
  isDayTradingClosed?: boolean;
  secondsToToggleIsDayTradingClosed?: number;
};

export function normalizePair(pair: PairLike): Record<string, unknown> {
  return {
    pair_id: pair.pairId ?? null,
    pair_from: pair.pairFrom ?? null,
    pair_to: pair.pairTo ?? null,
    venue_symbol: pair.pairFrom && pair.pairTo ? `${pair.pairFrom}-${pair.pairTo}` : null,
    category: pair.category ?? null,
    max_leverage: pair.maxLeverage ?? null,
    overnight_max_leverage: pair.overnightMaxLeverage ?? null,
    rollover_fee_per_block: pair.rolloverFeePerBlock ?? null,
    rollover_rate_long: pair.rolloverRate?.long ?? null,
    rollover_rate_short: pair.rolloverRate?.short ?? null,
    open_interest: pair.openInterest ?? null,
    buy_open_interest: pair.buyOpenInterest ?? null,
    sell_open_interest: pair.sellOpenInterest ?? null,
    max_open_interest: pair.maxOpenInterest ?? null,
    mid_px: pair.midPx ?? null,
    ask_px: pair.askPx ?? null,
    bid_px: pair.bidPx ?? null,
    is_market_open: pair.isMarketOpen ?? null,
    is_day_trading_closed: pair.isDayTradingClosed ?? null,
    seconds_to_toggle_is_day_trading_closed: pair.secondsToToggleIsDayTradingClosed ?? null
  };
}

export function buildPairsLine(args: {
  tsClient: string;
  pairs: PairLike[];
}): Record<string, unknown> {
  return {
    ts_client: args.tsClient,
    venue: "ostium",
    source: "ostium_builder_sdk_getPairs_v1",
    raw_payload_sha256: sha256Json(args.pairs),
    pairs: args.pairs.map(normalizePair),
    raw: { pairs: args.pairs }
  };
}

export async function main(): Promise<void> {
  const client = await OstiumClient.createReadOnly();
  const { pairs } = await client.getPairs();
  const line = buildPairsLine({ tsClient: new Date().toISOString(), pairs });
  const outPath = join(outDir, `pairs_${todayUtc()}.json`);
  await mkdir(dirname(outPath), { recursive: true });
  await writeFile(outPath, `${JSON.stringify(line, null, 2)}\n`, "utf8");
  console.log(`written: ${outPath} pairs=${pairs.length} sha256=${line.raw_payload_sha256}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err: unknown) => {
    console.error(err);
    process.exit(1);
  });
}

