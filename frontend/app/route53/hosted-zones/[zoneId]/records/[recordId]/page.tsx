"use client";

import Button from "@cloudscape-design/components/button";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { DeleteRecordModal } from "@/components/delete-record-modal";
import { LoadingScreen } from "@/components/loading-screen";
import { ResourceError } from "@/components/resource-error";
import { getDNSRecord } from "@/services/dns-records";

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
  const query = useQuery({
    queryKey: ["dns-record", zoneId, recordId],
    queryFn: ({ signal }) => getDNSRecord(zoneId, recordId, signal),
  });

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
    <SpaceBetween size="l">
      <Header
        variant="h1"
        description={`${record.record_type} record`}
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={() => setDeleteVisible(true)}>Delete</Button>
            <Button
              variant="primary"
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
        <div className="metadata-grid">
          <div>
            <div className="metadata-label">Record name</div>
            <div className="metadata-value">{record.fqdn}</div>
          </div>
          <div>
            <div className="metadata-label">Record ID</div>
            <div className="metadata-value">{record.id}</div>
          </div>
          <div>
            <div className="metadata-label">Record type</div>
            <div className="metadata-value">{record.record_type}</div>
          </div>
          <div>
            <div className="metadata-label">TTL</div>
            <div className="metadata-value">{record.ttl} seconds</div>
          </div>
          <div>
            <div className="metadata-label">Routing policy</div>
            <div className="metadata-value">Simple</div>
          </div>
          <div>
            <div className="metadata-label">Created</div>
            <div className="metadata-value">{formatDate(record.created_at)}</div>
          </div>
          <div>
            <div className="metadata-label">Last updated</div>
            <div className="metadata-value">{formatDate(record.updated_at)}</div>
          </div>
        </div>
      </Container>
      <Container header={<Header variant="h2">Values</Header>}>
        <SpaceBetween size="xs">
          {record.values.map((value, index) => (
            <div key={index}>{value}</div>
          ))}
        </SpaceBetween>
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
