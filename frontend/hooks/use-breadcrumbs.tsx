"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface BreadcrumbsContextValue {
  labels: Record<string, string>;
  setLabel: (key: string, label: string) => void;
}

const BreadcrumbsContext = createContext<BreadcrumbsContextValue>({
  labels: {},
  setLabel: () => {},
});

export function BreadcrumbsProvider({ children }: { children: ReactNode }) {
  const [labels, setLabels] = useState<Record<string, string>>({});

  const setLabel = useCallback((key: string, label: string) => {
    setLabels((prev) => {
      if (prev[key] === label) return prev;
      return { ...prev, [key]: label };
    });
  }, []);

  return (
    <BreadcrumbsContext.Provider value={{ labels, setLabel }}>
      {children}
    </BreadcrumbsContext.Provider>
  );
}

export function useBreadcrumbs() {
  return useContext(BreadcrumbsContext);
}
