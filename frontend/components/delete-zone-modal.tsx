"use client";

import Alert from "@cloudscape-design/components/alert";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Modal from "@cloudscape-design/components/modal";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNotifications } from "@/app/providers";
import { APIError } from "@/services/api";
import { deleteHostedZone } from "@/services/hosted-zones";
import type { HostedZone } from "@/types/api";

export function DeleteZoneModal({
  zone,
  visible,
  onDismiss,
  onDeleted,
}: {
  zone: HostedZone | null;
  visible: boolean;
  onDismiss: () => void;
  onDeleted: () => void;
}) {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const mutation = useMutation({
    mutationFn: () => deleteHostedZone(zone!.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["hosted-zones"] });
      queryClient.removeQueries({ queryKey: ["hosted-zone", zone!.id] });
      notify({
        type: "success",
        header: "Hosted zone deleted successfully.",
        content: `${zone!.name} was deleted.`,
      });
      onDeleted();
    },
  });
  const error = mutation.error instanceof APIError ? mutation.error.message : null;

  return (
    <Modal
      visible={visible}
      onDismiss={() => {
        if (!mutation.isPending) onDismiss();
      }}
      header="Delete hosted zone?"
      closeAriaLabel="Close dialog"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={onDismiss} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button
              variant="primary"
              loading={mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              Delete
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween size="m">
        {error && <Alert type="error">{error}</Alert>}
        <Box>
          You are about to delete <strong>{zone?.name}</strong>.
        </Box>
        <Box>
          All DNS records stored in this hosted zone will also be deleted. This
          action cannot be undone.
        </Box>
      </SpaceBetween>
    </Modal>
  );
}
