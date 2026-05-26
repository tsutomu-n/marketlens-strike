import { appendFile, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { rawEnvelope, schemaDigest, todayUtc } from "./artifacts.js";
import { sha256Json } from "./hash.js";
import { TARGET_PAIRS } from "./registry.js";
import { collectPricingFrames } from "./pricing_ws.js";

const outDir = process.env.GTRADE_PRICING_OUT_DIR ?? "../../data/raw/sidecar/gtrade-pricing";
const quarantineDir = process.env.GTRADE_PRICING_QUARANTINE_OUT_DIR ?? "../../data/raw/sidecar/gtrade-pricing-quarantine";
const network = process.env.GTRADE_NETWORK ?? "arbitrum";

function parseArgs(argv: string[]): { durationMinutes?: number; maxMessages?: number } {
  const result: { durationMinutes?: number; maxMessages?: number } = {};
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
    }
  }
  return result;
}

export async function main(argv: string[] = process.argv.slice(2)): Promise<void> {
  const args = parseArgs(argv);
  const outPath = join(outDir, `${todayUtc()}.jsonl`);
  const quarantinePath = join(quarantineDir, `${todayUtc()}.jsonl`);
  await mkdir(dirname(outPath), { recursive: true });
  await mkdir(dirname(quarantinePath), { recursive: true });

  const targetIndex = new Map(TARGET_PAIRS.map((item) => [item.pairIndex, item]));

  const count = await collectPricingFrames({
    durationMs: args.durationMinutes && Number.isFinite(args.durationMinutes) ? args.durationMinutes * 60_000 : undefined,
    maxMessages: args.maxMessages && Number.isFinite(args.maxMessages) ? args.maxMessages : undefined,
    onFrame: async ({ ts_client, parsed, raw }) => {
      const prices = [];
      const unknown = [];
      for (const point of parsed.points) {
        const target = targetIndex.get(point.pair_index);
        const row = {
          canonical_symbol: target?.canonicalSymbol ?? null,
          venue_symbol: target?.venueSymbol ?? null,
          pair_index: point.pair_index,
          mark_price: point.mark_price,
          index_price: point.index_price,
          mark_index_inferred_equal: point.mark_index_inferred_equal,
        };
        if (target) {
          prices.push(row);
        } else {
          unknown.push(row);
        }
      }
      if (!prices.length) return;

      const line = {
        ...rawEnvelope({
          source: "gtrade_pricing_v4",
          sourceEndpoint: process.env.GTRADE_PRICING_WS_URL ?? "wss://backend-pricing.eu.gains.trade/v4",
          body: raw,
          sourceTs: parsed.oracle_ts_ms,
        }),
        ts_client,
        venue: "gtrade",
        source: "gtrade_pricing_v4",
        network,
        prices,
        oracle_ts_ms: parsed.oracle_ts_ms,
        raw_payload_sha256: sha256Json(raw),
        pricing_schema_digest: schemaDigest(raw),
      };
      await appendFile(outPath, `${JSON.stringify(line)}\n`, "utf8");
      for (const item of unknown) {
        await appendFile(
          quarantinePath,
          `${JSON.stringify({
            ...rawEnvelope({
              source: "gtrade_pricing_v4_unknown_pair",
              sourceEndpoint: process.env.GTRADE_PRICING_WS_URL ?? "wss://backend-pricing.eu.gains.trade/v4",
              body: raw,
              sourceTs: parsed.oracle_ts_ms,
              extra: { pair_index: item.pair_index },
            }),
            venue: "gtrade",
            network,
            price: item,
          })}\n`,
          "utf8",
        );
      }
    },
  });

  console.log(`written: ${outPath} frames=${count}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err: unknown) => {
    console.error(err);
    process.exit(1);
  });
}
