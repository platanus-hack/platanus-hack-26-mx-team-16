"use client";

import { useCallback, useMemo, useState } from "react";
import { useSessionStore } from "@/src/application/contexts/session-store";
import { PaneSize } from "@/src/presentation/components/common/page-content";

function readStored(key: string, fallback: PaneSize): PaneSize {
  if (typeof window === "undefined") return fallback;
  try {
    const stored = window.localStorage.getItem(key);
    const valid = Object.values(PaneSize) as string[];
    if (stored !== null && valid.includes(stored)) {
      return stored as PaneSize;
    }
  } catch {
    // localStorage unavailable (private mode, quota, etc.).
  }
  return fallback;
}

export function usePersistedPaneSize(
  baseKey: string,
  defaultSize: PaneSize = PaneSize.Min
): [PaneSize, (next: PaneSize) => void] {
  const tenantUuid = useSessionStore((s) => s.tenant?.uuid ?? null);
  const userUuid = useSessionStore((s) => s.user?.uuid ?? null);

  // Persistence is namespaced per (tenant, user). If either is missing the
  // hook falls back to in-memory state and never touches localStorage.
  const storageKey = useMemo<string | null>(() => {
    if (!tenantUuid || !userUuid) return null;
    return `${baseKey}:${tenantUuid}:${userUuid}`;
  }, [baseKey, tenantUuid, userUuid]);

  const [size, setSize] = useState<PaneSize>(() =>
    storageKey ? readStored(storageKey, defaultSize) : defaultSize
  );

  const setPersisted = useCallback(
    (next: PaneSize) => {
      setSize(next);
      if (!storageKey || typeof window === "undefined") return;
      try {
        window.localStorage.setItem(storageKey, next);
      } catch {
        // Persisting is best-effort.
      }
    },
    [storageKey]
  );

  return [size, setPersisted];
}
