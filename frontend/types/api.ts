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
