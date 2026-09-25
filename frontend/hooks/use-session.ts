"use client";

import { useQuery } from "@tanstack/react-query";
import { getSession } from "@/services/auth";

export function useSession() {
  return useQuery({
    queryKey: ["session"],
    queryFn: ({ signal }) => getSession(signal),
  });
}
