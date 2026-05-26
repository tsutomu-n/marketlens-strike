import { mkdir, writeFile, appendFile } from "node:fs/promises";
import { dirname } from "node:path";
import { sha256Json } from "./hash.js";

export function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

export function recvTsMs(): number {
  return Date.now();
}

function schemaShape(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.length ? [schemaShape(value[0])] : [];
  }
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return Object.fromEntries(
      Object.keys(record)
        .sort()
        .map((key) => [key, schemaShape(record[key])]),
    );
  }
  return typeof value;
}

export function schemaDigest(value: unknown): string {
  return sha256Json(schemaShape(value));
}

export function rawEnvelope(args: {
  source: string;
  sourceEndpoint: string;
  body: unknown;
  sourceTs?: string | number | null;
  extra?: Record<string, unknown>;
}): Record<string, unknown> {
  return {
    recv_ts_ms: recvTsMs(),
    source_ts: args.sourceTs ?? null,
    source: args.source,
    source_endpoint: args.sourceEndpoint,
    body_digest: sha256Json(args.body),
    schema_digest: schemaDigest(args.body),
    ...args.extra,
    raw: args.body,
  };
}

export async function writeJson(path: string, value: unknown): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export async function appendJsonl(path: string, value: unknown): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  await appendFile(path, `${JSON.stringify(value)}\n`, "utf8");
}

