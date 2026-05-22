import { setTimeout as sleep } from "node:timers/promises";
import { pathToFileURL } from "node:url";
import { main as emitTradingVariablesOnce } from "./emit_jsonl.js";
import { main as collectPricing } from "./pricing_collector.js";

export type CollectWindowArgs = {
  durationMinutes: number;
  metadataIntervalSeconds: number;
};

export type CollectWindowDeps = {
  collectPricing: (argv: string[]) => Promise<void>;
  emitTradingVariablesOnce: () => Promise<void>;
  sleep: (ms: number) => Promise<void>;
  now: () => number;
};

const defaultDeps: CollectWindowDeps = {
  collectPricing,
  emitTradingVariablesOnce,
  sleep,
  now: Date.now,
};

function positiveInteger(value: number, name: string): number {
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${name} must be a positive integer`);
  }
  return value;
}

export function parseArgs(argv: string[]): CollectWindowArgs {
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

  return {
    durationMinutes: positiveInteger(durationMinutes, "--duration-minutes"),
    metadataIntervalSeconds: positiveInteger(metadataIntervalSeconds, "--metadata-interval-seconds"),
  };
}

export async function collectWindow(args: CollectWindowArgs, deps: CollectWindowDeps = defaultDeps): Promise<void> {
  const durationMinutes = positiveInteger(args.durationMinutes, "--duration-minutes");
  const metadataIntervalSeconds = positiveInteger(args.metadataIntervalSeconds, "--metadata-interval-seconds");
  const stopAt = deps.now() + durationMinutes * 60_000;

  let pricingSettled = false;
  let pricingError: unknown = null;
  const pricingTask = deps.collectPricing(["--duration-minutes", String(durationMinutes)])
    .then(undefined, (err: unknown) => {
      pricingError = err;
    })
    .finally(() => {
      pricingSettled = true;
    });

  while (deps.now() < stopAt && !pricingSettled) {
    await deps.emitTradingVariablesOnce();
    if (pricingError !== null) {
      throw pricingError;
    }
    const remaining = stopAt - deps.now();
    if (remaining <= 0) break;
    await Promise.race([
      deps.sleep(Math.min(metadataIntervalSeconds * 1000, remaining)),
      pricingTask,
    ]);
    if (pricingError !== null) {
      throw pricingError;
    }
  }

  await pricingTask;
  if (pricingError !== null) {
    throw pricingError;
  }
}

export async function main(argv: string[] = process.argv.slice(2)): Promise<void> {
  await collectWindow(parseArgs(argv));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err: unknown) => {
    console.error(err);
    process.exit(1);
  });
}
