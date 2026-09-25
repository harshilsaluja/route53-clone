"use client";

import Alert from "@cloudscape-design/components/alert";
import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Modal from "@cloudscape-design/components/modal";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNotifications } from "@/app/providers";
import { APIError } from "@/services/api";
import { deleteDNSRecord } from "@/services/dns-records";
import type { DNSRecord } from "@/types/api";

export function DeleteRecordModal({
  record,
  visible,
  onDismiss,
  onDeleted,
}: {
  record: DNSRecord | null;
  visible: boolean;
  onDismiss: () => void;
  onDeleted: () => void;
}) {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const mutation = useMutation({
    mutationFn: () => deleteDNSRecord(record!.hosted_zone_id, record!.id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["dns-records", record!.hosted_zone_id],
        }),
        queryClient.invalidateQueries({ queryKey: ["hosted-zones"] }),
        queryClient.invalidateQueries({
          queryKey: ["hosted-zone", record!.hosted_zone_id],
        }),
      ]);
      queryClient.removeQueries({
        queryKey: ["dns-record", record!.hosted_zone_id, record!.id],
      });
      notify({
        type: "success",
        header: "Record deleted successfully.",
        content: `${record!.fqdn} ${record!.record_type} was deleted.`,
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
      header="Delete record?"
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
          <strong>{record?.fqdn}</strong>
          <br />
          {record?.record_type}
        </Box>
        <Box>This record will be permanently deleted.</Box>
      </SpaceBetween>
    </Modal>
  );
}
