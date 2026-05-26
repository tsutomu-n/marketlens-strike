import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { appendJsonl, rawEnvelope, todayUtc, writeJson } from "./artifacts.js";
import { collectBackendEvents } from "./backend_ws.js";

const backendUrl = process.env.GTRADE_BACKEND_URL ?? "https://backend-arbitrum.gains.trade";
const backendWsUrl = process.env.GTRADE_BACKEND_WS_URL ?? "wss://backend-arbitrum.gains.trade";
const outDir = process.env.GTRADE_EVENT_OUT_DIR ?? "../../data/raw/sidecar/gtrade-backend";
const opsDir = process.env.GTRADE_EVENT_OPS_DIR ?? "../../data/ops";
const network = process.env.GTRADE_NETWORK ?? "arbitrum";
const collectorVersion = "gtrade_read_only_collector_v1";

export type EventCollectorArgs = {
  durationMinutes?: number;
  maxMessages?: number;
  runId: string;
  tradingVariablesPath: string;
  openTradesPath: string;
};

function parseArgs(argv: string[]): EventCollectorArgs {
  const result: EventCollectorArgs = {
    runId: new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14),
    tradingVariablesPath: process.env.GTRADE_TRADING_VARIABLES_PATH ?? "/trading-variables",
    openTradesPath: process.env.GTRADE_OPEN_TRADES_PATH ?? "/open-trades",
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--duration-minutes" && argv[i + 1]) {
      result.durationMinutes = Number(argv[i + 1]);
      i += 1;
      continue;
    }
    if (arg === "--max-messages" && argv[i + 1]) {
      result.maxMessages = Number(argv[i + 1]);
      i += 1;
      continue;
    }
    if (arg === "--run-id" && argv[i + 1]) {
      result.runId = argv[i + 1];
      i += 1;
      continue;
    }
    if (arg === "--trading-variables-path" && argv[i + 1]) {
      result.tradingVariablesPath = argv[i + 1];
      i += 1;
      continue;
    }
    if (arg === "--open-trades-path" && argv[i + 1]) {
      result.openTradesPath = argv[i + 1];
      i += 1;
    }
  }
  return result;
}

async function fetchJson(path: string): Promise<unknown> {
  const url = new URL(path, backendUrl).toString();
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<unknown>;
}

async function writeSnapshot(args: {
  day: string;
  runId: string;
  name: string;
  path: string;
  reason: string;
}): Promise<{ path: string; payload: unknown }> {
  const payload = await fetchJson(args.path);
  const outPath = join(outDir, "rest", args.day, `${args.runId}_${args.name}.json`);
  await writeJson(
    outPath,
    rawEnvelope({
      source: `gtrade_${args.name}`,
      sourceEndpoint: new URL(args.path, backendUrl).toString(),
      body: payload,
      extra: {
        venue: "gtrade",
        network,
        collector_version: collectorVersion,
        refresh_reason: args.reason,
      },
    }),
  );
  return { path: outPath, payload };
}

export async function main(argv: string[] = process.argv.slice(2)): Promise<void> {
  const args = parseArgs(argv);
  const day = todayUtc();
  const wsOutPath = join(outDir, "backend-ws", day, `${args.runId}.jsonl`);
  const manifestPath = join(outDir, "manifests", day, `${args.runId}.json`);
  const reconciliationPath = join(opsDir, `gtrade_state_reconciliation_${args.runId}.json`);

  const tradingVariables = await writeSnapshot({
    day,
    runId: args.runId,
    name: "trading_variables",
    path: args.tradingVariablesPath,
    reason: "initial_snapshot",
  });
  const openTrades = await writeSnapshot({
    day,
    runId: args.runId,
    name: "open_trades",
    path: args.openTradesPath,
    reason: "initial_snapshot",
  });

  const deepReorgRefreshes: string[] = [];
  const result = await collectBackendEvents({
    url: backendWsUrl,
    durationMs: args.durationMinutes && Number.isFinite(args.durationMinutes) ? args.durationMinutes * 60_000 : undefined,
    maxMessages: args.maxMessages && Number.isFinite(args.maxMessages) ? args.maxMessages : undefined,
    onEvent: async ({ recvTsMs, eventName, raw }) => {
      await appendJsonl(
        wsOutPath,
        rawEnvelope({
          source: "gtrade_backend_ws_v1",
          sourceEndpoint: backendWsUrl,
          body: raw,
          extra: {
            venue: "gtrade",
            network,
            collector_version: collectorVersion,
            recv_ts_ms: recvTsMs,
            event_name: eventName,
          },
        }),
      );
      if (eventName === "deepReorg") {
        const refresh = await writeSnapshot({
          day,
          runId: args.runId,
          name: `trading_variables_deep_reorg_${deepReorgRefreshes.length + 1}`,
          path: args.tradingVariablesPath,
          reason: "deepReorg",
        });
        deepReorgRefreshes.push(refresh.path);
      }
    },
  });

  const reconciliation = {
    venue: "gtrade",
    network,
    run_id: args.runId,
    status: "completed",
    rest_snapshot_paths: [tradingVariables.path, openTrades.path],
    backend_ws_path: wsOutPath,
    deep_reorg_detected: result.deepReorgCount > 0,
    deep_reorg_refresh_paths: deepReorgRefreshes,
    event_count: result.eventCount,
    reconnect_count: result.reconnectCount,
    notes: ["read_only_collector", "rest_snapshot_plus_backend_ws"],
  };
  await writeJson(reconciliationPath, reconciliation);

  await writeJson(manifestPath, {
    ...reconciliation,
    collector_version: collectorVersion,
    manifest_path: manifestPath,
    reconciliation_path: reconciliationPath,
    trading_variables_endpoint: new URL(args.tradingVariablesPath, backendUrl).toString(),
    open_trades_endpoint: new URL(args.openTradesPath, backendUrl).toString(),
  });

  console.log(`written_manifest: ${manifestPath}`);
  console.log(`written_backend_ws: ${wsOutPath}`);
  console.log(`written_reconciliation: ${reconciliationPath}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err: unknown) => {
    console.error(err);
    process.exit(1);
  });
}

