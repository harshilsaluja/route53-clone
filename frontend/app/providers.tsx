"use client";

import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { FlashbarProps } from "@cloudscape-design/components/flashbar";
import { BreadcrumbsProvider } from "@/hooks/use-breadcrumbs";
import { APIError } from "@/services/api";

type Notification = FlashbarProps.MessageDefinition;

interface NotificationsContextValue {
  notifications: Notification[];
  notify: (notification: Omit<Notification, "id" | "dismissible">) => void;
  dismiss: (id: string) => void;
}

const NotificationsContext = createContext<NotificationsContextValue | null>(null);

function unauthorized(error: unknown) {
  if (
    typeof window !== "undefined" &&
    error instanceof APIError &&
    error.status === 401 &&
    window.location.pathname !== "/login"
  ) {
    window.dispatchEvent(new Event("session-unauthorized"));
  }
}

export function Providers({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [queryClient] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({ onError: unauthorized }),
        mutationCache: new MutationCache({ onError: unauthorized }),
        defaultOptions: {
          queries: { staleTime: 30_000, retry: false },
          mutations: { retry: false },
        },
      }),
  );
  const dismiss = useCallback((id: string) => {
    setNotifications((current) => current.filter((item) => item.id !== id));
  }, []);
  const notify = useCallback(
    (notification: Omit<Notification, "id" | "dismissible">) => {
      const id = crypto.randomUUID();
      setNotifications((current) => [
        ...current,
        {
          ...notification,
          id,
          dismissible: true,
          onDismiss: () => dismiss(id),
        },
      ]);
    },
    [dismiss],
  );
  const value = useMemo(
    () => ({ notifications, notify, dismiss }),
    [notifications, notify, dismiss],
  );
  return (
    <QueryClientProvider client={queryClient}>
      <NotificationsContext.Provider value={value}>
        <BreadcrumbsProvider>{children}</BreadcrumbsProvider>
      </NotificationsContext.Provider>
    </QueryClientProvider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationsContext);
  if (!context) throw new Error("useNotifications must be used inside Providers");
  return context;
}
