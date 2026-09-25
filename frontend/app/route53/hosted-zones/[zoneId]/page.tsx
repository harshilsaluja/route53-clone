"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { Suspense, useState } from "react";
import { DeleteZoneModal } from "@/components/delete-zone-modal";
import { LoadingScreen } from "@/components/loading-screen";
import { RecordsTable } from "@/components/records-table";
import { ResourceError } from "@/components/resource-error";
import { getHostedZone } from "@/services/hosted-zones";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function HostedZoneDetailPage() {
  const { zoneId } = useParams<{ zoneId: string }>();
  const router = useRouter();
  const [deleteVisible, setDeleteVisible] = useState(false);
  const query = useQuery({
    queryKey: ["hosted-zone", zoneId],
    queryFn: ({ signal }) => getHostedZone(zoneId, signal),
  });

  if (query.isPending) return <LoadingScreen label="Loading hosted zone" />;
  if (query.error || !query.data) {
    return (
      <ResourceError
        error={query.error}
        retry={() => query.refetch()}
        resource="Hosted zone"
      />
    );
  }
  const zone = query.data;
  return (
    <SpaceBetween size="l">
      <Header
        variant="h1"
        description="Hosted zone details and DNS record summary."
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={() => setDeleteVisible(true)}>Delete</Button>
            <Button
              variant="primary"
              onClick={() =>
                router.push(`/route53/hosted-zones/${zone.id}/edit`)
              }
            >
              Edit
            </Button>
          </SpaceBetween>
        }
      >
        {zone.name}
      </Header>
      <Container header={<Header variant="h2">Hosted zone details</Header>}>
        <div className="metadata-grid">
          <div>
            <div className="metadata-label">Domain name</div>
            <div className="metadata-value">{zone.name}</div>
          </div>
          <div>
            <div className="metadata-label">Hosted Zone ID</div>
            <div className="metadata-value">{zone.id}</div>
          </div>
          <div>
            <div className="metadata-label">Type</div>
            <StatusIndicator type={zone.type === "PUBLIC" ? "success" : "info"}>
              {zone.type === "PUBLIC" ? "Public" : "Private"}
            </StatusIndicator>
          </div>
          <div>
            <div className="metadata-label">Record count</div>
            <div className="metadata-value">{zone.record_count}</div>
          </div>
          <div>
            <div className="metadata-label">Description</div>
            <div className="metadata-value">{zone.comment || "—"}</div>
          </div>
          <div>
            <div className="metadata-label">Created</div>
            <div className="metadata-value">{formatDate(zone.created_at)}</div>
          </div>
          <div>
            <div className="metadata-label">Last updated</div>
            <div className="metadata-value">{formatDate(zone.updated_at)}</div>
          </div>
        </div>
      </Container>
      <Suspense
        fallback={
          <Box color="text-body-secondary" padding="l">
            Loading records
          </Box>
        }
      >
        <RecordsTable zoneId={zone.id} />
      </Suspense>
      <DeleteZoneModal
        zone={zone}
        visible={deleteVisible}
        onDismiss={() => setDeleteVisible(false)}
        onDeleted={() => router.push("/route53/hosted-zones")}
      />
    </SpaceBetween>
  );
}
