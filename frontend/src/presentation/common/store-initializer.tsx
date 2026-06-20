"use client";

import { useEffect } from "react";

import { useTenantStore } from "@/src/application/stores/tenant-store";

let hasFetched = false;

export function StoreInitializer() {
  const fetchTenants = useTenantStore((s) => s.fetchTenants);

  useEffect(() => {
    if (hasFetched) return;
    hasFetched = true;
    fetchTenants();
  }, [fetchTenants]);

  return null;
}
