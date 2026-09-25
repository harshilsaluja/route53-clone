"use client";

import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useNotifications } from "@/app/providers";
import { LoadingScreen } from "@/components/loading-screen";
import { RecordForm } from "@/components/record-form";
import { ResourceError } from "@/components/resource-error";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";
import { createDNSRecord } from "@/services/dns-records";
import { getHostedZone } from "@/services/hosted-zones";
import type { DNSRecordCreate } from "@/types/api";

export default function CreateRecordPage() {
  const { zoneId } = useParams<{ zoneId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { setLabel } = useBreadcrumbs();

  const zoneQuery = useQuery({
    queryKey: ["hosted-zone", zoneId],
    queryFn: ({ signal }) => getHostedZone(zoneId, signal),
  });

  const zoneName = zoneQuery.data?.name;
  useEffect(() => {
    if (zoneName) {
      setLabel(zoneId, zoneName);
    }
  }, [zoneName, zoneId, setLabel]);

  const mutation = useMutation({
    mutationFn: (payload: DNSRecordCreate) =>
      createDNSRecord(zoneId, payload),
    onSuccess: async (record) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dns-records", zoneId] }),
        queryClient.invalidateQueries({ queryKey: ["hosted-zones"] }),
        queryClient.invalidateQueries({ queryKey: ["hosted-zone", zoneId] }),
      ]);
      queryClient.setQueryData(["dns-record", zoneId, record.id], record);
      notify({
        type: "success",
        header: "Record created successfully.",
        content: `${record.fqdn} ${record.record_type} was created.`,
      });
      router.push(`/route53/hosted-zones/${zoneId}`);
    },
  });

  if (zoneQuery.isPending) return <LoadingScreen label="Loading hosted zone" />;
  if (zoneQuery.error || !zoneQuery.data) {
    return (
      <ResourceError
        error={zoneQuery.error}
        retry={() => zoneQuery.refetch()}
        resource="Hosted zone"
      />
    );
  }

  return (
    <SpaceBetween size="m">
      <Header
        variant="h1"
        description={`Define DNS routing rules for ${zoneQuery.data.name}.`}
      >
        Create record
      </Header>
      <RecordForm
        mode="create"
        zoneName={zoneQuery.data.name}
        submitting={mutation.isPending}
        error={mutation.error}
        onSubmit={(payload) => mutation.mutate(payload)}
        onCancel={() => router.push(`/route53/hosted-zones/${zoneId}`)}
      />
    </SpaceBetween>
  );
}
