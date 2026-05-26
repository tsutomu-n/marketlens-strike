import { expect, test } from "bun:test";
import { collectBackendEvents, type BackendWebSocketLike } from "./backend_ws.js";

type Listener = (event?: unknown) => void | Promise<void>;

class FakeWebSocket implements BackendWebSocketLike {
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

function createFakeWebSocket(url: string): BackendWebSocketLike {
  return new FakeWebSocket(url);
}

test("collectBackendEvents rejects unbounded collection", async () => {
  await expect(
    collectBackendEvents({
      url: "ws://example.test",
      createWebSocket: createFakeWebSocket,
      onEvent: () => {},
    }),
  ).rejects.toThrow("Either maxMessages or durationMs is required");
});

test("collectBackendEvents persists event names and deepReorg count", async () => {
  FakeWebSocket.instances = [];
  const names: string[] = [];

  const promise = collectBackendEvents({
    url: "ws://example.test",
    maxMessages: 2,
    createWebSocket: createFakeWebSocket,
    onEvent: (frame) => {
      names.push(frame.eventName);
    },
  });

  while (FakeWebSocket.instances.length === 0) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
  FakeWebSocket.instances[0].dispatch("message", { data: JSON.stringify({ event: "registerTrade" }) });
  FakeWebSocket.instances[0].dispatch("message", { data: JSON.stringify({ event: "deepReorg" }) });

  const result = await promise;
  expect(result.eventCount).toBe(2);
  expect(result.deepReorgCount).toBe(1);
  expect(names).toEqual(["registerTrade", "deepReorg"]);
});

