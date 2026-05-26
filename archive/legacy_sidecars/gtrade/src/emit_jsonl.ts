import { appendFile, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { fetchTradingVariables } from "./fetch_trading_variables.js";
import { sha256Json } from "./hash.js";
import { TARGET_PAIRS, type TargetPair } from "./registry.js";

const backendUrl = process.env.GTRADE_BACKEND_URL ?? "https://backend-arbitrum.gains.trade";
const network = process.env.GTRADE_NETWORK ?? "arbitrum";
const outDir = process.env.GTRADE_OUT_DIR ?? "../../data/raw/sidecar/gtrade";

function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

function pickArray(value: unknown, key: string): unknown[] {
  const record = asRecord(value);
  const candidate = record?.[key];
  return Array.isArray(candidate) ? candidate : [];
}

function pickArrayItemByIndex(items: unknown[], pairIndex: number): Record<string, unknown> | null {
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

function pickMapItemByIndex(value: unknown, pairIndex: number): Record<string, unknown> | null {
  const record = asRecord(value);
  const direct = record?.[String(pairIndex)];
  return asRecord(direct);
}

function pickIndexedRecord(value: unknown, key: string, pairIndex: number): Record<string, unknown> | null {
  const parent = asRecord(value);
  const candidate = parent?.[key];
  return pickArrayItemByIndex(Array.isArray(candidate) ? candidate : [], pairIndex)
    ?? pickMapItemByIndex(candidate, pairIndex);
}

export function toBps(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return null;
  return numeric / 1e8;
}

export function extractPair(target: TargetPair, transformed: unknown, raw: unknown): Record<string, unknown> {
  const rawPair = pickIndexedRecord(raw, "pairs", target.pairIndex);
  const transformedPair = pickIndexedRecord(transformed, "pairs", target.pairIndex);
  const source = rawPair ?? transformedPair ?? {};
  const pairInfo = pickIndexedRecord(raw, "pairInfos", target.pairIndex)
    ?? pickIndexedRecord(transformed, "pairInfos", target.pairIndex);
  const feeIndex = source.feeIndex ?? source.fee_index ?? null;
  const groupIndex = source.groupIndex ?? source.group_index ?? null;
  const fee = feeIndex === null ? null : pickArrayItemByIndex(pickArray(raw, "fees"), Number(feeIndex));
  const group = groupIndex === null ? null : pickArrayItemByIndex(pickArray(raw, "groups"), Number(groupIndex));

  const spreadRaw = pairInfo?.spreadP ?? source.spreadP ?? source.spreadP_raw ?? null;
  return {
    canonical_symbol: target.canonicalSymbol,
    venue_symbol: target.venueSymbol,
    pair_index: target.pairIndex,
    asset_class: target.assetClass,
    pair_from: source.from ?? null,
    pair_to: source.to ?? null,
    spreadP_raw: spreadRaw,
    spread_bps: toBps(spreadRaw),
    fee_index: feeIndex,
    group_index: groupIndex,
    group_name: group?.name ?? null,
    min_leverage: group?.minLeverage ?? group?.min_leverage ?? null,
    max_leverage: group?.maxLeverage ?? group?.max_leverage ?? source.maxLeverage ?? source.max_leverage ?? null,
    total_position_size_fee_p: fee?.totalPositionSizeFeeP ?? null,
    min_position_size_usd: fee?.minPositionSizeUsd ?? null,
    one_percent_depth_above_usd: pairInfo?.onePercentDepthAboveUsd ?? null,
    one_percent_depth_below_usd: pairInfo?.onePercentDepthBelowUsd ?? null,
    oi_long_usd: source.oiLongUsd ?? null,
    oi_short_usd: source.oiShortUsd ?? null
  };
}

export function buildSidecarLine(args: {
  tsClient: string;
  network: string;
  backendUrl: string;
  raw: unknown;
  transformed: unknown;
}): Record<string, unknown> {
  const rawPayloadSha256 = sha256Json(args.raw);
  const rawRecord = asRecord(args.raw) ?? {};
  return {
    ts_client: args.tsClient,
    venue: "gtrade",
    network: args.network,
    backend: args.backendUrl,
    pairs: TARGET_PAIRS.map((target) => extractPair(target, args.transformed, args.raw)),
    market_status: {
      isForexOpen: rawRecord.isForexOpen ?? null,
      isStocksOpen: rawRecord.isStocksOpen ?? null,
      isIndicesOpen: rawRecord.isIndicesOpen ?? null,
      isCommoditiesOpen: rawRecord.isCommoditiesOpen ?? null
    },
    raw_payload_sha256: rawPayloadSha256,
    raw: args.raw,
    transformed: args.transformed
  };
}

export async function main(): Promise<void> {
  const snapshot = await fetchTradingVariables(backendUrl);
  const rawPayloadSha256 = sha256Json(snapshot.raw);
  const line = buildSidecarLine({
    tsClient: new Date().toISOString(),
    network,
    backendUrl,
    raw: snapshot.raw,
    transformed: snapshot.transformed
  });

  const outPath = join(outDir, `${todayUtc()}.jsonl`);
  await mkdir(dirname(outPath), { recursive: true });
  await appendFile(outPath, `${JSON.stringify(line)}\n`, "utf8");
  console.log(`written: ${outPath} sha256=${rawPayloadSha256}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err: unknown) => {
    console.error(err);
    process.exit(1);
  });
}
