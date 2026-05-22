import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { OstiumClient, type PairPosition } from "@ostium/builder-sdk";
import { sha256Json } from "./hash.js";

const outDir = process.env.OSTIUM_OUT_DIR ?? "../../data/raw/sidecar/ostium";

function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

function userFromArgs(): string | null {
  const userFlagIndex = process.argv.findIndex((arg) => arg === "--user");
  if (userFlagIndex >= 0) {
    return process.argv[userFlagIndex + 1] ?? null;
  }
  const prefixed = process.argv.find((arg) => arg.startsWith("--user="));
  if (prefixed) {
    return prefixed.slice("--user=".length);
  }
  return process.env.OSTIUM_USER_ADDRESS ?? null;
}

function limitFromArgs(): number | undefined {
  const limitFlagIndex = process.argv.findIndex((arg) => arg === "--limit");
  const raw = limitFlagIndex >= 0
    ? process.argv[limitFlagIndex + 1]
    : process.argv.find((arg) => arg.startsWith("--limit="))?.slice("--limit=".length);
  if (!raw) {
    return undefined;
  }
  const limit = Number(raw);
  if (!Number.isInteger(limit) || limit < 1) {
    throw new Error("Ostium positions --limit must be a positive integer");
  }
  return limit;
}

function sanitizeUser(user: string): string {
  return user.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function normalizeUser(user: string): `0x${string}` | "ALL" {
  if (user === "ALL") {
    return user;
  }
  if (!/^0x[a-fA-F0-9]{40}$/.test(user)) {
    throw new Error("Ostium user must be an EVM address like 0x... or ALL");
  }
  return user as `0x${string}`;
}

export function normalizePosition(pairPosition: PairPosition): Record<string, unknown> {
  const position = pairPosition.position;
  return {
    pair_id: position.pairId,
    pair_from: position.pairFrom,
    pair_to: position.pairTo,
    venue_symbol: `${position.pairFrom}-${position.pairTo}`,
    pid: position.pid,
    idx: position.idx,
    side: position.side === "B" ? "long" : "short",
    size: position.szi,
    entry_px: position.entryPx,
    leverage: position.leverage,
    notional_usd: position.ntl,
    unrealized_pnl_usd: position.unrealizedPnl,
    return_on_equity: position.returnOnEquity,
    liquidation_px: position.liquidationPx,
    collateral_used_usd: position.collateralUsed,
    cumulative_rollover_usd: position.cumRollover,
    take_profit_px: position.tpPx ?? null,
    stop_loss_px: position.slPx ?? null,
    open_timestamp_ms: position.openTimestamp,
    is_day_trade: position.isDayTrade,
    max_leverage: position.maxLeverage,
    max_withdrawable_usd: position.maxWithdrawable
  };
}

export function buildPositionsLine(args: {
  tsClient: string;
  user: string;
  response: { pairPositions: PairPosition[]; marginSummary: unknown; time: number };
}): Record<string, unknown> {
  return {
    ts_client: args.tsClient,
    venue: "ostium",
    source: "ostium_builder_sdk_getOpenPositions_v1",
    user: args.user,
    server_time_ms: args.response.time,
    raw_payload_sha256: sha256Json(args.response),
    position_count: args.response.pairPositions.length,
    positions: args.response.pairPositions.map(normalizePosition),
    margin_summary: args.response.marginSummary,
    raw: args.response
  };
}

export async function main(): Promise<void> {
  const user = userFromArgs();
  if (!user) {
    throw new Error("Missing --user or OSTIUM_USER_ADDRESS for read-only open-position probe");
  }

  const limit = limitFromArgs();
  const client = await OstiumClient.createReadOnly();
  const normalizedUser = normalizeUser(user);
  const response = await client.getOpenPositions({ user: normalizedUser, limit });
  const line = buildPositionsLine({ tsClient: new Date().toISOString(), user, response });
  const outPath = join(outDir, `positions_${sanitizeUser(user)}_${todayUtc()}.json`);
  await mkdir(dirname(outPath), { recursive: true });
  await writeFile(outPath, `${JSON.stringify(line, null, 2)}\n`, "utf8");
  console.log(
    `written: ${outPath} positions=${line.position_count} sha256=${line.raw_payload_sha256}`
  );
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err: unknown) => {
    console.error(err);
    process.exit(1);
  });
}
