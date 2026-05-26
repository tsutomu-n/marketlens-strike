import { transformGlobalTradingVariables } from "@gainsnetwork/sdk";

export type TradingVariablesSnapshot = {
  backendUrl: string;
  raw: unknown;
  transformed: unknown;
};

export async function fetchTradingVariables(backendUrl: string): Promise<TradingVariablesSnapshot> {
  const response = await fetch(`${backendUrl}/trading-variables`);
  if (!response.ok) {
    throw new Error(`Failed to fetch trading-variables: ${response.status} ${response.statusText}`);
  }

  const raw = await response.json();
  const transformed = transformGlobalTradingVariables(raw);

  return { backendUrl, raw, transformed };
}

