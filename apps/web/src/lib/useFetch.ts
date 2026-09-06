// Tiny data hook: fetch on mount (and whenever `tick` changes) with reload.

import { useCallback, useEffect, useState } from "react";

export interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** Re-run the fetch. */
  reload: () => void;
}

export function useFetch<T>(path: string | null): FetchState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const reload = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (!path) return;
    let active = true;
    setLoading(true);
    setError(null);
    fetch(path)
      .then(async (res) => {
        if (!res.ok) {
          let detail = `${res.status}`;
          try {
            const d = (await res.json()) as { detail?: string };
            if (d.detail) detail = d.detail;
          } catch {
            /* keep */
          }
          throw new Error(detail);
        }
        return res.json() as Promise<T>;
      })
      .then((value) => {
        if (active) setData(value);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path, tick]);

  return { data, loading, error, reload };
}

/** Poll GET /path until `predicate(data)` is true or timeout (default 90s). */
export async function pollUntil<T>(
  path: string,
  predicate: (data: T) => boolean,
  opts: { intervalMs?: number; timeoutMs?: number } = {},
): Promise<T> {
  const { intervalMs = 600, timeoutMs = 90_000 } = opts;
  const start = Date.now();
  for (;;) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = (await res.json()) as T;
    if (predicate(data)) return data;
    if (Date.now() - start > timeoutMs) throw new Error("timed out waiting for run");
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
