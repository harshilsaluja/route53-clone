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
import { getDNSRecord, updateDNSRecord } from "@/services/dns-records";
import { getHostedZone } from "@/services/hosted-zones";
import type { DNSRecordCreate } from "@/types/api";

export default function EditRecordPage() {
  const { zoneId, recordId } = useParams<{
    zoneId: string;
    recordId: string;
  }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { setLabel } = useBreadcrumbs();

  const zoneQuery = useQuery({
    queryKey: ["hosted-zone", zoneId],
    queryFn: ({ signal }) => getHostedZone(zoneId, signal),
  });
  const recordQuery = useQuery({
    queryKey: ["dns-record", zoneId, recordId],
    queryFn: ({ signal }) => getDNSRecord(zoneId, recordId, signal),
  });

  const zoneName = zoneQuery.data?.name;
  const recordFqdn = recordQuery.data?.fqdn;

  useEffect(() => {
    if (zoneName) {
      setLabel(zoneId, zoneName);
    }
    if (recordFqdn) {
      setLabel(recordId, recordFqdn);
    }
  }, [zoneName, recordFqdn, zoneId, recordId, setLabel]);

  const mutation = useMutation({
    mutationFn: (payload: DNSRecordCreate) =>
      updateDNSRecord(zoneId, recordId, payload),
    onSuccess: async (record) => {
      queryClient.setQueryData(["dns-record", zoneId, recordId], record);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dns-records", zoneId] }),
        queryClient.invalidateQueries({ queryKey: ["hosted-zones"] }),
        queryClient.invalidateQueries({ queryKey: ["hosted-zone", zoneId] }),
      ]);
      notify({
        type: "success",
        header: "Record updated successfully.",
        content: `${record.fqdn} ${record.record_type} was updated.`,
      });
      router.push(
        `/route53/hosted-zones/${zoneId}/records/${record.id}`,
      );
    },
  });

  if (zoneQuery.isPending || recordQuery.isPending) {
    return <LoadingScreen label="Loading record" />;
  }
  if (zoneQuery.error || !zoneQuery.data) {
    return (
      <ResourceError
        error={zoneQuery.error}
        retry={() => zoneQuery.refetch()}
        resource="Hosted zone"
      />
    );
  }
  if (recordQuery.error || !recordQuery.data) {
    return (
      <ResourceError
        error={recordQuery.error}
        retry={() => recordQuery.refetch()}
        resource="Record"
      />
    );
  }

  return (
    <SpaceBetween size="m">
      <Header
        variant="h1"
        description={`Update the ${recordQuery.data.record_type} record set.`}
      >
        Edit {recordQuery.data.fqdn}
      </Header>
      <RecordForm
        key={recordQuery.data.updated_at}
        mode="edit"
        zoneName={zoneQuery.data.name}
        initial={recordQuery.data}
        submitting={mutation.isPending}
        error={mutation.error}
        onSubmit={(payload) => mutation.mutate(payload)}
        onCancel={() =>
          router.push(
            `/route53/hosted-zones/${zoneId}/records/${recordId}`,
          )
        }
      />
    </SpaceBetween>
  );
}
