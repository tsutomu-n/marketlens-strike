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
  createWebSocket?: (url: string) => PricingWebSocketLike;
  onFrame: (frame: PricingFrame) => Promise<void> | void;
};

export type PricingWebSocketLike = {
  close: () => void;
  addEventListener: (type: string, listener: (event: MessageEvent) => void | Promise<void>) => void;
};

export async function collectPricingFrames(options: PricingWsOptions): Promise<number> {
  const url = options.url ?? process.env.GTRADE_PRICING_WS_URL ?? "wss://backend-pricing.eu.gains.trade/v4";
  const maxFromEnv = Number(process.env.GTRADE_PRICING_MAX_MESSAGES ?? 0);
  const maxMessages = options.maxMessages ?? (Number.isFinite(maxFromEnv) && maxFromEnv > 0 ? maxFromEnv : undefined);
  const durationMs = options.durationMs ?? 0;
  const reconnectDelayMs = options.reconnectDelayMs ?? 1000;
  const hasMaxMessages = maxMessages !== undefined && maxMessages > 0;
  const hasDuration = durationMs > 0;
  if (!hasMaxMessages && !hasDuration) {
    throw new Error("Either maxMessages or durationMs is required");
  }
  const stopAt = durationMs > 0 ? Date.now() + durationMs : null;
  const createWebSocket = options.createWebSocket ?? ((wsUrl: string) => new WebSocket(wsUrl));

  let count = 0;
  while (true) {
    if (hasMaxMessages && count >= maxMessages) break;
    if (stopAt !== null && Date.now() >= stopAt) break;

    const result = await new Promise<"closed" | "errored">((resolve, reject) => {
      const ws = createWebSocket(url);
      let closed = false;
      let settled = false;
      const timeout =
        stopAt === null
          ? undefined
          : setTimeout(() => {
              closeOnce();
              resolveOnce("closed");
            }, Math.max(0, stopAt - Date.now()));

      const resolveOnce = (value: "closed" | "errored"): void => {
        if (settled) return;
        settled = true;
        if (timeout !== undefined) clearTimeout(timeout);
        resolve(value);
      };

      const rejectOnce = (err: unknown): void => {
        if (settled) return;
        settled = true;
        if (timeout !== undefined) clearTimeout(timeout);
        reject(err);
      };

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
          if (hasMaxMessages && count >= maxMessages) {
            closeOnce();
            resolveOnce("closed");
          }
          if (stopAt !== null && Date.now() >= stopAt) {
            closeOnce();
            resolveOnce("closed");
          }
        } catch (err) {
          closeOnce();
          rejectOnce(err);
        }
      });

      ws.addEventListener("error", () => {
        closeOnce();
        resolveOnce("errored");
      });

      ws.addEventListener("close", () => resolveOnce("closed"));
    });

    if (hasMaxMessages && count >= maxMessages) break;
    if (stopAt !== null && Date.now() >= stopAt) break;
    if (result === "errored") {
      await new Promise((resolve) => setTimeout(resolve, reconnectDelayMs));
    }
  }

  return count;
}
