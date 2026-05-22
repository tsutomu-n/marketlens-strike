import { parsePricingPayload, type ParsedPricingPayload } from "./pricing_parser.js";

export type PricingFrame = {
  ts_client: string;
  parsed: ParsedPricingPayload;
  raw: unknown;
};

export type PricingWsOptions = {
  url?: string;
  maxMessages?: number;
  durationMs?: number;
  reconnectDelayMs?: number;
  onFrame: (frame: PricingFrame) => Promise<void> | void;
};

export async function collectPricingFrames(options: PricingWsOptions): Promise<number> {
  const url = options.url ?? process.env.GTRADE_PRICING_WS_URL ?? "wss://backend-pricing.eu.gains.trade/v4";
  const maxFromEnv = Number(process.env.GTRADE_PRICING_MAX_MESSAGES ?? 0);
  const maxMessages = options.maxMessages ?? (Number.isFinite(maxFromEnv) && maxFromEnv > 0 ? maxFromEnv : undefined);
  const durationMs = options.durationMs ?? 0;
  const reconnectDelayMs = options.reconnectDelayMs ?? 1000;
  const stopAt = durationMs > 0 ? Date.now() + durationMs : null;

  let count = 0;
  while (true) {
    if (maxMessages && count >= maxMessages) break;
    if (stopAt !== null && Date.now() >= stopAt) break;

    const result = await new Promise<"closed" | "errored">((resolve, reject) => {
      const ws = new WebSocket(url);
      let closed = false;

      const closeOnce = (): void => {
        if (!closed) {
          closed = true;
          ws.close();
        }
      };

      ws.addEventListener("open", () => {
        // Gains v4 pushes without subscription payload.
      });

      ws.addEventListener("message", async (event: MessageEvent) => {
        try {
          const data = typeof event.data === "string" ? event.data : String(event.data);
          const raw = JSON.parse(data) as unknown;
          const parsed = parsePricingPayload(raw);
          await options.onFrame({ ts_client: new Date().toISOString(), parsed, raw });
          count += 1;
          if (maxMessages && count >= maxMessages) {
            closeOnce();
          }
          if (stopAt !== null && Date.now() >= stopAt) {
            closeOnce();
          }
        } catch (err) {
          closeOnce();
          reject(err);
        }
      });

      ws.addEventListener("error", () => {
        closeOnce();
        resolve("errored");
      });

      ws.addEventListener("close", () => resolve("closed"));
    });

    if (maxMessages && count >= maxMessages) break;
    if (stopAt !== null && Date.now() >= stopAt) break;
    if (result === "errored") {
      await new Promise((resolve) => setTimeout(resolve, reconnectDelayMs));
    }
  }

  return count;
}
