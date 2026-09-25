"use client";

import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useNotifications } from "@/app/providers";
import { LoadingScreen } from "@/components/loading-screen";
import { ResourceError } from "@/components/resource-error";
import { ZoneForm } from "@/components/zone-form";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";
import { getHostedZone, updateHostedZone } from "@/services/hosted-zones";
import type { HostedZoneCreate } from "@/types/api";

export default function EditHostedZonePage() {
  const { zoneId } = useParams<{ zoneId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
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

  const mutation = useMutation({
    mutationFn: (payload: HostedZoneCreate) =>
      updateHostedZone(zoneId, payload),
    onSuccess: async (updatedZone) => {
      queryClient.setQueryData(["hosted-zone", zoneId], updatedZone);
      await queryClient.invalidateQueries({ queryKey: ["hosted-zones"] });
      notify({
        type: "success",
        header: "Hosted zone updated successfully.",
        content: `${updatedZone.name} was updated.`,
      });
      router.push(`/route53/hosted-zones/${updatedZone.id}`);
    },
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
    <SpaceBetween size="m">
      <Header variant="h1" description="Update the hosted zone configuration.">
        Edit {zone.name}
      </Header>
      <ZoneForm
        key={zone.updated_at}
        mode="edit"
        initial={{ name: zone.name, comment: zone.comment, type: zone.type }}
        submitting={mutation.isPending}
        error={mutation.error}
        onSubmit={(value) => mutation.mutate(value)}
        onCancel={() => router.push(`/route53/hosted-zones/${zone.id}`)}
      />
    </SpaceBetween>
  );
}
