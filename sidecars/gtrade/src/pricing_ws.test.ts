import { expect, test } from "bun:test";
import { collectPricingFrames, type PricingWebSocketLike } from "./pricing_ws.js";

type Listener = (event?: unknown) => void | Promise<void>;

class FakeWebSocket implements PricingWebSocketLike {
  static instances: FakeWebSocket[] = [];
  readonly listeners = new Map<string, Listener[]>();
  closeCount = 0;

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  addEventListener(type: string, listener: Listener): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close(): void {
    this.closeCount += 1;
    this.dispatch("close");
  }

  dispatch(type: string, event?: unknown): void {
    for (const listener of this.listeners.get(type) ?? []) {
      void listener(event);
    }
  }
}

function createFakeWebSocket(url: string): PricingWebSocketLike {
  return new FakeWebSocket(url);
}

test("collectPricingFrames rejects unbounded collection", async () => {
  await expect(
    collectPricingFrames({
      url: "ws://example.test",
      createWebSocket: createFakeWebSocket,
      onFrame: () => {},
    }),
  ).rejects.toThrow("Either maxMessages or durationMs is required");
});

test("collectPricingFrames stops on duration even when no messages arrive", async () => {
  FakeWebSocket.instances = [];

  const count = await collectPricingFrames({
    url: "ws://example.test",
    durationMs: 5,
    createWebSocket: createFakeWebSocket,
    onFrame: () => {},
  });

  expect(count).toBe(0);
  expect(FakeWebSocket.instances).toHaveLength(1);
  expect(FakeWebSocket.instances[0].closeCount).toBe(1);
});

test("collectPricingFrames stops at maxMessages", async () => {
  FakeWebSocket.instances = [];
  let frames = 0;

  const promise = collectPricingFrames({
    url: "ws://example.test",
    maxMessages: 1,
    createWebSocket: createFakeWebSocket,
    onFrame: () => {
      frames += 1;
    },
  });

  while (FakeWebSocket.instances.length === 0) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
  FakeWebSocket.instances[0].dispatch("message", {
    data: JSON.stringify({ t: 1779457500000, prices: { "86": { m: 1, i: 1 } } }),
  });

  const count = await promise;
  expect(count).toBe(1);
  expect(frames).toBe(1);
  expect(FakeWebSocket.instances[0].closeCount).toBe(1);
});
