import { apiRequest } from "@/services/api";
import type {
  DNSRecord,
  DNSRecordCreate,
  DNSRecordType,
  DNSRecordUpdate,
  PaginatedDNSRecords,
} from "@/types/api";

export interface DNSRecordListParameters {
  search?: string;
  record_type?: DNSRecordType;
  page?: number;
  page_size?: number;
}

function base(zoneId: string) {
  return `/hosted-zones/${zoneId}/records`;
}

export function listDNSRecords(
  zoneId: string,
  parameters: DNSRecordListParameters,
  signal?: AbortSignal,
) {
  const query = new URLSearchParams();
  if (parameters.search) query.set("search", parameters.search);
  if (parameters.record_type) {
    query.set("record_type", parameters.record_type);
  }
  query.set("page", String(parameters.page ?? 1));
  query.set("page_size", String(parameters.page_size ?? 20));
  return apiRequest<PaginatedDNSRecords>(
    `${base(zoneId)}?${query.toString()}`,
    {},
    signal,
  );
}

export function getDNSRecord(
  zoneId: string,
  recordId: string,
  signal?: AbortSignal,
) {
  return apiRequest<DNSRecord>(`${base(zoneId)}/${recordId}`, {}, signal);
}

export function createDNSRecord(zoneId: string, payload: DNSRecordCreate) {
  return apiRequest<DNSRecord>(base(zoneId), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateDNSRecord(
  zoneId: string,
  recordId: string,
  payload: DNSRecordUpdate,
) {
  return apiRequest<DNSRecord>(`${base(zoneId)}/${recordId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteDNSRecord(zoneId: string, recordId: string) {
  return apiRequest<void>(`${base(zoneId)}/${recordId}`, {
    method: "DELETE",
  });
}
