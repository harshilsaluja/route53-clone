export type HostedZoneType = "PUBLIC" | "PRIVATE";

export interface User {
  id: string;
  email: string;
  display_name: string;
}

export interface SessionResponse {
  user: User;
  expires_at: string;
}

export interface HostedZone {
  id: string;
  name: string;
  type: HostedZoneType;
  comment: string | null;
  record_count: number;
  created_at: string;
  updated_at: string;
}

export interface HostedZoneCreate {
  name: string;
  type: HostedZoneType;
  comment: string | null;
}

export type HostedZoneUpdate = Partial<HostedZoneCreate>;

export interface PaginationMetadata {
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface PaginatedHostedZones {
  items: HostedZone[];
  pagination: PaginationMetadata;
}

export type DNSRecordType =
  | "A"
  | "AAAA"
  | "CNAME"
  | "TXT"
  | "MX"
  | "NS"
  | "PTR"
  | "SRV"
  | "CAA";

export interface DNSRecord {
  id: string;
  hosted_zone_id: string;
  name: string;
  fqdn: string;
  record_type: DNSRecordType;
  ttl: number;
  routing_policy: "SIMPLE";
  values: string[];
  created_at: string;
  updated_at: string;
}

export interface DNSRecordCreate {
  name: string;
  record_type: DNSRecordType;
  ttl: number;
  routing_policy: "SIMPLE";
  values: string[];
}

export type DNSRecordUpdate = Partial<DNSRecordCreate>;

export interface PaginatedDNSRecords {
  items: DNSRecord[];
  pagination: PaginationMetadata;
}

export interface ValidationDetail {
  field: string;
  message: string;
}

export interface APIErrorBody {
  error: {
    code: string;
    message: string;
    details?: ValidationDetail[];
  };
}
