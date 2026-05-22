import { setTimeout as sleep } from "node:timers/promises";
import { pathToFileURL } from "node:url";
import { main as emitTradingVariablesOnce } from "./emit_jsonl.js";
import { main as collectPricing } from "./pricing_collector.js";

function parseArgs(argv: string[]): { durationMinutes: number; metadataIntervalSeconds: number } {
  let durationMinutes = 60;
  let metadataIntervalSeconds = 60;

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--duration-minutes" && argv[i + 1]) {
      durationMinutes = Number(argv[i + 1]);
      i += 1;
      continue;
    }
    if (arg === "--metadata-interval-seconds" && argv[i + 1]) {
      metadataIntervalSeconds = Number(argv[i + 1]);
      i += 1;
    }
  }

  return { durationMinutes, metadataIntervalSeconds };
}

export async function main(argv: string[] = process.argv.slice(2)): Promise<void> {
  const args = parseArgs(argv);
  const stopAt = Date.now() + Math.max(1, args.durationMinutes) * 60_000;

  const pricingTask = collectPricing(["--duration-minutes", String(args.durationMinutes)]);

  while (Date.now() < stopAt) {
    await emitTradingVariablesOnce();
    const remaining = stopAt - Date.now();
    if (remaining <= 0) break;
    await sleep(Math.min(args.metadataIntervalSeconds * 1000, remaining));
  }

  await pricingTask;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err: unknown) => {
    console.error(err);
    process.exit(1);
  });
}
