import { expect, test } from "bun:test";
import { collectWindow, parseArgs, type CollectWindowDeps } from "./collect_window.js";

test("parseArgs rejects invalid collection durations", () => {
  expect(() => parseArgs(["--duration-minutes", "0"])).toThrow("--duration-minutes must be a positive integer");
  expect(() => parseArgs(["--duration-minutes", "0.5"])).toThrow("--duration-minutes must be a positive integer");
  expect(() => parseArgs(["--metadata-interval-seconds", "NaN"])).toThrow(
    "--metadata-interval-seconds must be a positive integer",
  );
});

test("collectWindow fails fast when pricing collection fails during metadata sleep", async () => {
  let metadataCount = 0;
  let rejectPricing: (err: Error) => void = () => {};
  const pricingFailure = new Promise<void>((_, reject) => {
    rejectPricing = reject;
  });
  const deps: CollectWindowDeps = {
    collectPricing: () => pricingFailure,
    emitTradingVariablesOnce: async () => {
      metadataCount += 1;
      rejectPricing(new Error("pricing failed"));
    },
    sleep: () => new Promise<void>(() => {}),
    now: () => 0,
  };

  await expect(
    collectWindow({ durationMinutes: 120, metadataIntervalSeconds: 60 }, deps),
  ).rejects.toThrow("pricing failed");
  expect(metadataCount).toBe(1);
});
