"use client";

import Alert from "@cloudscape-design/components/alert";
import Button from "@cloudscape-design/components/button";
import { APIError } from "@/services/api";

export function ResourceError({
  error,
  retry,
  resource = "resource",
}: {
  error: unknown;
  retry: () => void;
  resource?: string;
}) {
  const notFound = error instanceof APIError && error.status === 404;
  return (
    <Alert
      type="error"
      header={notFound ? `${resource} not found` : `Unable to load ${resource.toLowerCase()}`}
      action={<Button onClick={retry}>Try again</Button>}
    >
      {notFound
        ? "It may have been deleted, or you may not have access to it."
        : error instanceof APIError
          ? error.message
          : "An unexpected error occurred."}
    </Alert>
  );
}
