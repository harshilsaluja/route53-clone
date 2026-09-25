"use client";

import Box from "@cloudscape-design/components/box";
import Badge from "@cloudscape-design/components/badge";
import Button from "@cloudscape-design/components/button";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Tabs from "@cloudscape-design/components/tabs";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { DeleteZoneModal } from "@/components/delete-zone-modal";
import { useNotifications } from "@/app/providers";
import { LoadingScreen } from "@/components/loading-screen";
import { RecordsTable } from "@/components/records-table";
import { ResourceError } from "@/components/resource-error";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";
import { listDNSRecords } from "@/services/dns-records";
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
  const [exporting, setExporting] = useState(false);
  const { setLabel } = useBreadcrumbs();
  const { notify } = useNotifications();

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

  const exportJSON = async () => {
    setExporting(true);
    try {
      const records = [];
      let page = 1;
      let pages = 1;
      do {
        const response = await listDNSRecords(zone.id, { page, page_size: 100 });
        records.push(...response.items);
        pages = response.pagination.pages;
        page += 1;
      } while (page <= pages);
      const payload = {
        hosted_zone: { id: zone.id, name: zone.name, type: zone.type, comment: zone.comment },
        records: records.map(({ name, fqdn, record_type, ttl, routing_policy, values }) => ({
          name, fqdn, record_type, ttl, routing_policy, values,
        })),
      };
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${zone.name.replace(/[^a-z0-9.-]/gi, "-")}-route53.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      notify({ type: "success", header: "Hosted zone exported successfully." });
    } catch {
      notify({ type: "error", header: "Hosted zone export failed.", content: "Try the export again." });
    } finally {
      setExporting(false);
    }
  };

  return (
    <SpaceBetween size="m">
      <Header
        variant="h1"
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button iconName="download" loading={exporting} onClick={exportJSON}>Export JSON</Button>
            <Button onClick={() => setDeleteVisible(true)}>Delete zone</Button>
            <Button
              onClick={() =>
                router.push(`/route53/hosted-zones/${zone.id}/edit`)
              }
            >
              Edit hosted zone
            </Button>
          </SpaceBetween>
        }
      >
        <span className="aws-zone-title"><Badge color={zone.type === "PUBLIC" ? "blue" : "grey"}>{zone.type === "PUBLIC" ? "Public" : "Private"}</Badge>{zone.name}</span>
      </Header>
      <div className="aws-details-section">
      <ExpandableSection variant="container" defaultExpanded headerText="Hosted zone details">
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
      </ExpandableSection>
      </div>
      <div className="aws-zone-tabs">
        <Tabs tabs={[
          { id: "records", label: `Records (${zone.record_count})`, content: (
            <Suspense fallback={<Box color="text-body-secondary" padding="l">Loading records</Box>}><RecordsTable zoneId={zone.id} /></Suspense>
          ) },
          { id: "recovery", label: "Accelerated recovery", content: <Box padding="l" color="text-body-secondary">Accelerated recovery is not available in this assignment.</Box> },
          { id: "dnssec", label: "DNSSEC signing", content: <Box padding="l" color="text-body-secondary">DNSSEC signing is not available in this assignment.</Box> },
          { id: "tags", label: "Hosted zone tags (0)", content: <Box padding="l" color="text-body-secondary">Hosted zone tags are not available in this assignment.</Box> },
        ]} />
      </div>
      <DeleteZoneModal
        zone={zone}
        visible={deleteVisible}
        onDismiss={() => setDeleteVisible(false)}
        onDeleted={() => router.push("/route53/hosted-zones")}
      />
    </SpaceBetween>
  );
}
