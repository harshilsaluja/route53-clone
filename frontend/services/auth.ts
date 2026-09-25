import { apiRequest } from "@/services/api";
import type { SessionResponse } from "@/types/api";

export function login(email: string, password: string, signal?: AbortSignal) {
  return apiRequest<SessionResponse>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
    signal,
  );
}

export function getSession(signal?: AbortSignal) {
  return apiRequest<SessionResponse>("/auth/me", {}, signal);
}

export function logout() {
  return apiRequest<void>("/auth/logout", { method: "POST" });
}
