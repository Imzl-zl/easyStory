import { requestJson } from "@/lib/api/client";
import type {
  ConfigRegistryDetail,
  ConfigRegistryObject,
  ConfigRegistrySummary,
  ConfigRegistryType,
} from "@/lib/api/types";

function buildConfigRegistryPath(type: ConfigRegistryType, itemId?: string): string {
  const basePath = `/api/v1/config/${type}`;
  return itemId ? `${basePath}/${itemId}` : basePath;
}

export function listConfigRegistryEntries(type: ConfigRegistryType) {
  return requestJson<ConfigRegistrySummary[]>(buildConfigRegistryPath(type));
}

export function getConfigRegistryEntry(type: ConfigRegistryType, itemId: string) {
  return requestJson<ConfigRegistryDetail>(buildConfigRegistryPath(type, itemId));
}

export function updateConfigRegistryEntry(
  type: ConfigRegistryType,
  itemId: string,
  payload: ConfigRegistryObject,
) {
  return requestJson<ConfigRegistryDetail>(buildConfigRegistryPath(type, itemId), {
    body: payload,
    method: "PUT",
  });
}
