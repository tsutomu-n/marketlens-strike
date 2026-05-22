import { appendFile, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { sha256Json } from "./hash.js";
import { TARGET_PAIRS } from "./registry.js";
import { collectPricingFrames } from "./pricing_ws.js";

const outDir = process.env.GTRADE_PRICING_OUT_DIR ?? "../../data/raw/sidecar/gtrade-pricing";
const network = process.env.GTRADE_NETWORK ?? "arbitrum";

function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

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
  await mkdir(dirname(outPath), { recursive: true });

  const targetIndex = new Map(TARGET_PAIRS.map((item) => [item.pairIndex, item]));

  const count = await collectPricingFrames({
    durationMs: args.durationMinutes && Number.isFinite(args.durationMinutes) ? args.durationMinutes * 60_000 : undefined,
    maxMessages: args.maxMessages && Number.isFinite(args.maxMessages) ? args.maxMessages : undefined,
    onFrame: async ({ ts_client, parsed, raw }) => {
      const prices = parsed.points
        .filter((point) => targetIndex.has(point.pair_index))
        .map((point) => {
          const target = targetIndex.get(point.pair_index);
          return {
            canonical_symbol: target?.canonicalSymbol ?? null,
            venue_symbol: target?.venueSymbol ?? null,
            pair_index: point.pair_index,
            mark_price: point.mark_price,
            index_price: point.index_price,
          };
        });
      if (!prices.length) return;

      const line = {
        ts_client,
        venue: "gtrade",
        source: "gtrade_pricing_v4",
        network,
        prices,
        oracle_ts_ms: parsed.oracle_ts_ms,
        raw_payload_sha256: sha256Json(raw),
      };
      await appendFile(outPath, `${JSON.stringify(line)}\n`, "utf8");
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
