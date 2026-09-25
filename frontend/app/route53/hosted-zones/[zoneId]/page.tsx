"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { DeleteZoneModal } from "@/components/delete-zone-modal";
import { LoadingScreen } from "@/components/loading-screen";
import { RecordsTable } from "@/components/records-table";
import { ResourceError } from "@/components/resource-error";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";
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
  const { setLabel } = useBreadcrumbs();

  const query = useQuery({
    queryKey: ["hosted-zone", zoneId],
    queryFn: ({ signal }) => getHostedZone(zoneId, signal),
  });

  const zoneName = query.data?.name;
  useEffect(() => {
    if (zoneName) {
      setLabel(zoneId, zoneName);
    }
  }, [zoneName, zoneId, setLabel]);

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
    <SpaceBetween size="m">
      <Header
        variant="h1"
        description={`${zone.type === "PUBLIC" ? "Public" : "Private"} hosted zone`}
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={() => setDeleteVisible(true)}>Delete</Button>
            <Button
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
        <ColumnLayout columns={4} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">Domain name</Box>
            <div>{zone.name}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Hosted zone ID</Box>
            <div>{zone.id}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Type</Box>
            <div>{zone.type === "PUBLIC" ? "Public" : "Private"}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Record count</Box>
            <div>{zone.record_count}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Description</Box>
            <div>{zone.comment || "—"}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Created</Box>
            <div>{formatDate(zone.created_at)}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Last updated</Box>
            <div>{formatDate(zone.updated_at)}</div>
          </div>
        </ColumnLayout>
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
