export type BackendEventFrame = {
  recvTsMs: number;
  eventName: string;
  raw: unknown;
};

export type BackendWsOptions = {
  url?: string;
  maxMessages?: number;
  durationMs?: number;
  reconnectDelayMs?: number;
  createWebSocket?: (url: string) => BackendWebSocketLike;
  onEvent: (frame: BackendEventFrame) => Promise<void> | void;
};

export type BackendWebSocketLike = {
  close: () => void;
  addEventListener: (type: string, listener: (event: MessageEvent) => void | Promise<void>) => void;
};

function eventNameFromPayload(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "unknown";
  const record = payload as Record<string, unknown>;
  const direct = record.event ?? record.name ?? record.type ?? record.eventName;
  if (typeof direct === "string" && direct) return direct;
  const payloadRecord = record.payload;
  if (payloadRecord && typeof payloadRecord === "object") {
    const nested = payloadRecord as Record<string, unknown>;
    const nestedName = nested.event ?? nested.name ?? nested.type ?? nested.eventName;
    if (typeof nestedName === "string" && nestedName) return nestedName;
  }
  return "unknown";
}

export async function collectBackendEvents(options: BackendWsOptions): Promise<{
  eventCount: number;
  reconnectCount: number;
  deepReorgCount: number;
}> {
  const url = options.url ?? process.env.GTRADE_BACKEND_WS_URL ?? "wss://backend-arbitrum.gains.trade";
  const maxFromEnv = Number(process.env.GTRADE_BACKEND_WS_MAX_MESSAGES ?? 0);
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
  let eventCount = 0;
  let reconnectCount = 0;
  let deepReorgCount = 0;

  while (true) {
    if (hasMaxMessages && eventCount >= maxMessages) break;
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

      ws.addEventListener("message", async (event: MessageEvent) => {
        try {
          const data = typeof event.data === "string" ? event.data : String(event.data);
          const raw = JSON.parse(data) as unknown;
          const eventName = eventNameFromPayload(raw);
          if (eventName === "deepReorg") {
            deepReorgCount += 1;
          }
          await options.onEvent({ recvTsMs: Date.now(), eventName, raw });
          eventCount += 1;
          if (hasMaxMessages && eventCount >= maxMessages) {
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

    if (hasMaxMessages && eventCount >= maxMessages) break;
    if (stopAt !== null && Date.now() >= stopAt) break;
    if (result === "errored") {
      reconnectCount += 1;
      await new Promise((resolve) => setTimeout(resolve, reconnectDelayMs));
    }
  }

  return { eventCount, reconnectCount, deepReorgCount };
}

