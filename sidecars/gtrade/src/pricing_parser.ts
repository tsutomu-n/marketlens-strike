export type PricingPoint = {
  pair_index: number;
  mark_price: number | null;
  index_price: number | null;
};

export type ParsedPricingPayload = {
  oracle_ts_ms: number | null;
  points: PricingPoint[];
};

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | null {
  return value && typeof value === "object" ? (value as UnknownRecord) : null;
}

function toFiniteNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function parsePoint(input: unknown): PricingPoint | null {
  const row = asRecord(input);
  if (!row) return null;

  const pairIndex = toFiniteNumber(row.pairIndex ?? row.pair_index ?? row.index ?? row.p);
  if (pairIndex === null) return null;

  return {
    pair_index: Math.trunc(pairIndex),
    mark_price: toFiniteNumber(row.m ?? row.mark ?? row.mark_price),
    index_price: toFiniteNumber(row.i ?? row.index ?? row.index_price),
  };
}

export function parsePricingPayload(payload: unknown): ParsedPricingPayload {
  const root = asRecord(payload) ?? {};
  const t = toFiniteNumber(root.t ?? root.ts ?? root.timestamp ?? null);

  let entries: unknown[] = [];
  const prices = root.prices;
  if (Array.isArray(prices)) {
    entries = prices;
  } else if (prices && typeof prices === "object") {
    entries = Object.entries(prices as UnknownRecord).map(([k, v]) => {
      const row = asRecord(v) ?? {};
      return { ...row, pairIndex: row.pairIndex ?? row.pair_index ?? Number(k) };
    });
  }

  if (!entries.length && Array.isArray(root.m) && Array.isArray(root.i)) {
    const marks = root.m as unknown[];
    const indices = root.i as unknown[];
    entries = marks.map((mark, idx) => ({ pairIndex: idx, m: mark, i: indices[idx] }));
  }

  const points: PricingPoint[] = [];
  for (const entry of entries) {
    const point = parsePoint(entry);
    if (point) points.push(point);
  }

  return {
    oracle_ts_ms: t === null ? null : Math.trunc(t),
    points,
  };
}
