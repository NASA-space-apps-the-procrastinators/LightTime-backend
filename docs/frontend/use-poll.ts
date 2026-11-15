"use client";
// Copy to src/lib/use-poll.ts. Pass a stable function such as api.crew, or wrap it in useCallback.
import { useEffect, useState } from "react";

export function usePoll<T>(load: () => Promise<T>, everyMs = 1000): { data: T | null; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    const tick = async () => {
      try {
        const next = await load();
        if (live) { setData(next); setError(null); }
      } catch (problem) {
        if (live) setError(String(problem));
      }
    };
    void tick();
    const timer = setInterval(tick, everyMs);
    return () => { live = false; clearInterval(timer); };
  }, [load, everyMs]);
  return { data, error };
}
