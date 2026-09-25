import { apiRequest } from "@/services/api";
import type {
  HostedZone,
  HostedZoneCreate,
  HostedZoneType,
  HostedZoneUpdate,
  PaginatedHostedZones,
} from "@/types/api";

export interface HostedZoneListParameters {
  search?: string;
  type?: HostedZoneType;
  page?: number;
  page_size?: number;
}

export function listHostedZones(
  parameters: HostedZoneListParameters,
  signal?: AbortSignal,
) {
  const query = new URLSearchParams();
  if (parameters.search) query.set("search", parameters.search);
  if (parameters.type) query.set("type", parameters.type);
  query.set("page", String(parameters.page ?? 1));
  query.set("page_size", String(parameters.page_size ?? 20));
  return apiRequest<PaginatedHostedZones>(
    `/hosted-zones?${query.toString()}`,
    {},
    signal,
  );
}

export function getHostedZone(id: string, signal?: AbortSignal) {
  return apiRequest<HostedZone>(`/hosted-zones/${id}`, {}, signal);
}

export function createHostedZone(payload: HostedZoneCreate) {
  return apiRequest<HostedZone>("/hosted-zones", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateHostedZone(id: string, payload: HostedZoneUpdate) {
  return apiRequest<HostedZone>(`/hosted-zones/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteHostedZone(id: string) {
  return apiRequest<void>(`/hosted-zones/${id}`, { method: "DELETE" });
}
