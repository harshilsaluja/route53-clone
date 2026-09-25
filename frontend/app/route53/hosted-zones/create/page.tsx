"use client";

import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useNotifications } from "@/app/providers";
import { ZoneForm } from "@/components/zone-form";
import { createHostedZone } from "@/services/hosted-zones";

export default function CreateHostedZonePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const mutation = useMutation({
    mutationFn: createHostedZone,
    onSuccess: async (zone) => {
      await queryClient.invalidateQueries({ queryKey: ["hosted-zones"] });
      queryClient.setQueryData(["hosted-zone", zone.id], zone);
      notify({
        type: "success",
        header: "Hosted zone created successfully.",
        content: `${zone.name} is ready to manage.`,
      });
      router.push(`/route53/hosted-zones/${zone.id}`);
    },
  });

  return (
    <SpaceBetween size="l">
      <Header
        variant="h1"
        description="Create a public or private DNS namespace."
      >
        Create hosted zone
      </Header>
      <ZoneForm
        mode="create"
        submitting={mutation.isPending}
        error={mutation.error}
        onSubmit={(value) => mutation.mutate(value)}
        onCancel={() => router.push("/route53/hosted-zones")}
      />
    </SpaceBetween>
  );
}
