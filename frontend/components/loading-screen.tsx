"use client";

import Box from "@cloudscape-design/components/box";
import Spinner from "@cloudscape-design/components/spinner";
import SpaceBetween from "@cloudscape-design/components/space-between";

export function LoadingScreen({ label = "Loading" }: { label?: string }) {
  return (
    <div className="loading-screen">
      <SpaceBetween size="s" direction="horizontal" alignItems="center">
        <Spinner size="large" />
        <Box color="text-body-secondary">{label}</Box>
      </SpaceBetween>
    </div>
  );
}
