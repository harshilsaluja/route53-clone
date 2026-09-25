import type { APIErrorBody, ValidationDetail } from "@/types/api";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "");

export class APIError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: ValidationDetail[] = [],
  ) {
    super(message);
    this.name = "APIError";
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      signal,
      credentials: "include",
      headers: {
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new APIError(
      0,
      "NETWORK_ERROR",
      "Unable to reach the API. Confirm that the backend is running.",
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const body = (await response.json().catch(() => null)) as APIErrorBody | T | null;
  if (!response.ok) {
    const error = body as APIErrorBody | null;
    throw new APIError(
      response.status,
      error?.error?.code ?? "API_ERROR",
      error?.error?.message ?? "The request could not be completed.",
      error?.error?.details ?? [],
    );
  }
  return body as T;
}
