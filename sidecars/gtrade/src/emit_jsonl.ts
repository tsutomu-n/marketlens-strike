import { appendFile, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fetchTradingVariables } from "./fetch_trading_variables.js";
import { sha256Json } from "./hash.js";
import { TARGET_PAIRS, type TargetPair } from "./registry.js";

const backendUrl = process.env.GTRADE_BACKEND_URL ?? "https://backend-arbitrum.gains.trade";
const network = process.env.GTRADE_NETWORK ?? "arbitrum";
const outDir = process.env.GTRADE_OUT_DIR ?? "../../data/raw/sidecar/gtrade";

function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

function pickArray(value: unknown, key: string): unknown[] {
  const record = value as Record<string, unknown>;
  const candidate = record?.[key];
  return Array.isArray(candidate) ? candidate : [];
}

function pickByIndex(items: unknown[], pairIndex: number): Record<string, unknown> | null {
  const direct = items[pairIndex];
  if (direct && typeof direct === "object") {
    return direct as Record<string, unknown>;
  }
  const matched = items.find((item) => {
    if (!item || typeof item !== "object") return false;
    const record = item as Record<string, unknown>;
    return record.pairIndex === pairIndex || record.pair_index === pairIndex || record.index === pairIndex;
  });
  return matched && typeof matched === "object" ? (matched as Record<string, unknown>) : null;
}

function toBps(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return null;
  return numeric / 1e8;
}

function extractPair(target: TargetPair, transformed: unknown, raw: unknown): Record<string, unknown> {
  const transformedPair = pickByIndex(pickArray(transformed, "pairs"), target.pairIndex);
  const rawPair = pickByIndex(pickArray(raw, "pairs"), target.pairIndex);
  const pairInfo = pickByIndex(pickArray(transformed, "pairInfos"), target.pairIndex)
    ?? pickByIndex(pickArray(raw, "pairInfos"), target.pairIndex);
  const source = transformedPair ?? rawPair ?? {};

  const spreadRaw = pairInfo?.spreadP ?? source.spreadP ?? source.spreadP_raw ?? null;
  return {
    canonical_symbol: target.canonicalSymbol,
    venue_symbol: target.venueSymbol,
    pair_index: target.pairIndex,
    asset_class: target.assetClass,
    spreadP_raw: spreadRaw,
    spread_bps: toBps(spreadRaw),
    fee_index: source.feeIndex ?? source.fee_index ?? null,
    group_index: source.groupIndex ?? source.group_index ?? null,
    max_leverage: source.maxLeverage ?? source.max_leverage ?? null,
    one_percent_depth_above_usd: pairInfo?.onePercentDepthAboveUsd ?? null,
    one_percent_depth_below_usd: pairInfo?.onePercentDepthBelowUsd ?? null,
    oi_long_usd: source.oiLongUsd ?? null,
    oi_short_usd: source.oiShortUsd ?? null
  };
}

async function main(): Promise<void> {
  const snapshot = await fetchTradingVariables(backendUrl);
  const tsClient = new Date().toISOString();
  const rawPayloadSha256 = sha256Json(snapshot.raw);
  const rawRecord = snapshot.raw as Record<string, unknown>;

  const line = {
    ts_client: tsClient,
    venue: "gtrade",
    network,
    backend: backendUrl,
    pairs: TARGET_PAIRS.map((target) => extractPair(target, snapshot.transformed, snapshot.raw)),
    market_status: {
      isForexOpen: rawRecord.isForexOpen ?? null,
      isStocksOpen: rawRecord.isStocksOpen ?? null,
      isIndicesOpen: rawRecord.isIndicesOpen ?? null,
      isCommoditiesOpen: rawRecord.isCommoditiesOpen ?? null
    },
    raw_payload_sha256: rawPayloadSha256,
    raw: snapshot.raw,
    transformed: snapshot.transformed
  };

  const outPath = join(outDir, `${todayUtc()}.jsonl`);
  await mkdir(dirname(outPath), { recursive: true });
  await appendFile(outPath, `${JSON.stringify(line)}\n`, "utf8");
  console.log(`written: ${outPath}`);
}

main().catch((err: unknown) => {
  console.error(err);
  process.exit(1);
});

