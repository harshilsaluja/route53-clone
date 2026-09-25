"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { DeleteRecordModal } from "@/components/delete-record-modal";
import { LoadingScreen } from "@/components/loading-screen";
import { ResourceError } from "@/components/resource-error";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";
import { getDNSRecord } from "@/services/dns-records";
import { getHostedZone } from "@/services/hosted-zones";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function RecordDetailPage() {
  const { zoneId, recordId } = useParams<{
    zoneId: string;
    recordId: string;
  }>();
  const router = useRouter();
  const [deleteVisible, setDeleteVisible] = useState(false);
  const { setLabel } = useBreadcrumbs();

  const zoneQuery = useQuery({
    queryKey: ["hosted-zone", zoneId],
    queryFn: ({ signal }) => getHostedZone(zoneId, signal),
  });

  const query = useQuery({
    queryKey: ["dns-record", zoneId, recordId],
    queryFn: ({ signal }) => getDNSRecord(zoneId, recordId, signal),
  });

  const zoneName = zoneQuery.data?.name;
  const recordFqdn = query.data?.fqdn;

  useEffect(() => {
    if (zoneName) {
      setLabel(zoneId, zoneName);
    }
    if (recordFqdn) {
      setLabel(recordId, recordFqdn);
    }
  }, [zoneName, recordFqdn, zoneId, recordId, setLabel]);

  if (query.isPending) return <LoadingScreen label="Loading record" />;
  if (query.error || !query.data) {
    return (
      <ResourceError
        error={query.error}
        retry={() => query.refetch()}
        resource="Record"
      />
    );
  }
  const record = query.data;

  return (
    <SpaceBetween size="m">
      <Header
        variant="h1"
        description={`${record.record_type} record set`}
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={() => setDeleteVisible(true)}>Delete</Button>
            <Button
              onClick={() =>
                router.push(
                  `/route53/hosted-zones/${zoneId}/records/${recordId}/edit`,
                )
              }
            >
              Edit
            </Button>
          </SpaceBetween>
        }
      >
        {record.fqdn}
      </Header>
      <Container header={<Header variant="h2">Record details</Header>}>
        <ColumnLayout columns={4} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">Record name</Box>
            <div>{record.fqdn}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Record ID</Box>
            <div>{record.id}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Record type</Box>
            <div>{record.record_type}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">TTL</Box>
            <div>{record.ttl} seconds</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Routing policy</Box>
            <div>Simple routing</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Created</Box>
            <div>{formatDate(record.created_at)}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Last updated</Box>
            <div>{formatDate(record.updated_at)}</div>
          </div>
        </ColumnLayout>
      </Container>
      <Container header={<Header variant="h2">Value / Route traffic to</Header>}>
        <div className="record-values-cell">
          <SpaceBetween size="xs">
            {record.values.map((value, index) => (
              <div key={index} className="record-values-item">{value}</div>
            ))}
          </SpaceBetween>
        </div>
      </Container>
      <DeleteRecordModal
        record={record}
        visible={deleteVisible}
        onDismiss={() => setDeleteVisible(false)}
        onDeleted={() => router.push(`/route53/hosted-zones/${zoneId}`)}
      />
    </SpaceBetween>
  );
}
