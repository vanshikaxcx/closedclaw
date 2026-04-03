import { getLiveAdapter } from "@/lib/adapters/live";
import { getMockAdapter } from "@/lib/adapters/mock";
import type { DataAdapter } from "@/lib/adapters/types";

let singleton: DataAdapter | null = null;

export function getDataAdapter(): DataAdapter {
  if (singleton) {
    return singleton;
  }

  const mode = process.env.NEXT_PUBLIC_ADAPTER_MODE?.toLowerCase();
  singleton = mode === "live" ? getLiveAdapter() : getMockAdapter();
  return singleton;
}
