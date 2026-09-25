"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Header from "@cloudscape-design/components/header";
import Link from "@cloudscape-design/components/link";
import Pagination from "@cloudscape-design/components/pagination";
import Select, { type SelectProps } from "@cloudscape-design/components/select";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Table, { type TableProps } from "@cloudscape-design/components/table";
import TextFilter from "@cloudscape-design/components/text-filter";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { DeleteRecordModal } from "@/components/delete-record-modal";
import { ResourceError } from "@/components/resource-error";
import { listDNSRecords } from "@/services/dns-records";
import type { DNSRecord, DNSRecordType } from "@/types/api";

const recordTypes: DNSRecordType[] = [
  "A", "AAAA", "CNAME", "TXT", "MX", "NS", "PTR", "SRV", "CAA",
];
const typeOptions: SelectProps.Option[] = [
  { label: "All record types", value: "ALL" },
  ...recordTypes.map((value) => ({ label: value, value })),
];

function Values({ values }: { values: string[] }) {
  const shown = values.slice(0, 3);
  return (
    <div className="record-values-cell">
      {shown.map((value, index) => (
        <div key={index} className="record-values-item">{value}</div>
      ))}
      {values.length > shown.length && (
        <Box color="text-body-secondary" fontSize="body-s">
          +{values.length - shown.length} more
        </Box>
      )}
    </div>
  );
}

export function RecordsTable({ zoneId }: { zoneId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const search = searchParams.get("search") ?? "";
  const typeValue = searchParams.get("record_type");
  const recordType = recordTypes.includes(typeValue as DNSRecordType)
    ? (typeValue as DNSRecordType)
    : undefined;
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const [searchText, setSearchText] = useState(search);
  const [selected, setSelected] = useState<DNSRecord[]>([]);
  const [deleteVisible, setDeleteVisible] = useState(false);

  const updateUrl = (updates: Record<string, string | undefined>) => {
    const next = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    router.replace(
      `/route53/hosted-zones/${zoneId}?${next.toString()}`,
    );
  };

  useEffect(() => {
    if (searchText === search) return;
    const timeout = window.setTimeout(
      () => updateUrl({ search: searchText.trim() || undefined, page: undefined }),
      300,
    );
    return () => window.clearTimeout(timeout);
    // URL changes intentionally restart this small debounce.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchText, search]);

  const query = useQuery({
    queryKey: [
      "dns-records",
      zoneId,
      { search, recordType, page, pageSize: 20 },
    ],
    queryFn: ({ signal }) =>
      listDNSRecords(
        zoneId,
        { search, record_type: recordType, page, page_size: 20 },
        signal,
      ),
    placeholderData: keepPreviousData,
  });
  const items = query.data?.items ?? [];
  const pagination = query.data?.pagination;
  const columns = useMemo<TableProps.ColumnDefinition<DNSRecord>[]>(
    () => [
      {
        id: "name",
        header: "Record name",
        cell: (record) => (
          <Link
            href={`/route53/hosted-zones/${zoneId}/records/${record.id}`}
            fontSize="body-m"
          >
            {record.fqdn}
          </Link>
        ),
      },
      { id: "type", header: "Type", cell: (record) => record.record_type },
      {
        id: "routing",
        header: "Routing policy",
        cell: () => "Simple",
      },
      {
        id: "values",
        header: "Value / Route traffic to",
        cell: (record) => <Values values={record.values} />,
      },
      { id: "ttl", header: "TTL", cell: (record) => record.ttl },
    ],
    [zoneId],
  );

  return (
    <SpaceBetween size="m">
      {query.error && (
        <ResourceError
          error={query.error}
          retry={() => query.refetch()}
          resource="Records"
        />
      )}
      <div className="aws-resource-split aws-records-split">
      <div className="aws-console-table">
      <Table
        items={items}
        columnDefinitions={columns}
        trackBy="id"
        selectionType="single"
        selectedItems={selected}
        onSelectionChange={({ detail }) => setSelected(detail.selectedItems)}
        loading={query.isPending || query.isFetching}
        loadingText="Loading records"
        header={
          <Header
            variant="h2"
            counter={pagination ? `(${pagination.total})` : undefined}
            description="DNS records stored in this hosted zone."
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button iconName="refresh" ariaLabel="Refresh records" onClick={() => query.refetch()} />
                <Button
                  disabled={selected.length !== 1}
                  onClick={() => selected[0] && router.push(`/route53/hosted-zones/${zoneId}/records/${selected[0].id}/edit`)}
                >
                  Edit
                </Button>
                <Button
                  disabled={selected.length !== 1}
                  onClick={() => setDeleteVisible(true)}
                >
                  Delete
                </Button>
                <span className="aws-create-action"><Button
                    variant="primary"
                    onClick={() => router.push(`/route53/hosted-zones/${zoneId}/records/create`)}
                  >Create record</Button></span>
              </SpaceBetween>
            }
          >
            Records
          </Header>
        }
        filter={
          <SpaceBetween direction="horizontal" size="s">
            <TextFilter
              filteringText={searchText}
              filteringPlaceholder="Find records"
              filteringAriaLabel="Find records"
              countText={
                pagination
                  ? `${pagination.total} ${pagination.total === 1 ? "match" : "matches"}`
                  : undefined
              }
              onChange={({ detail }) => setSearchText(detail.filteringText)}
            />
            <div className="filter-select-wrapper">
              <Select
                ariaLabel="Filter by record type"
                selectedOption={
                  typeOptions.find(
                    (option) => option.value === (recordType ?? "ALL"),
                  ) ?? typeOptions[0]
                }
                options={typeOptions}
                onChange={({ detail }) =>
                  updateUrl({
                    record_type:
                      detail.selectedOption.value === "ALL"
                        ? undefined
                        : detail.selectedOption.value,
                    page: undefined,
                  })
                }
              />
            </div>
          </SpaceBetween>
        }
        pagination={
          <Pagination
            currentPageIndex={page}
            pagesCount={Math.max(1, pagination?.pages ?? 1)}
            onChange={({ detail }) =>
              updateUrl({
                page:
                  detail.currentPageIndex === 1
                    ? undefined
                    : String(detail.currentPageIndex),
              })
            }
            ariaLabels={{
              nextPageLabel: "Next page",
              previousPageLabel: "Previous page",
              pageLabel: (pageNumber) => `Page ${pageNumber}`,
            }}
          />
        }
        empty={
          <Box textAlign="center" color="inherit">
            <SpaceBetween size="m">
              <b>{search || recordType ? "No matching records" : "No records"}</b>
              <Box color="text-body-secondary">
                {search || recordType
                  ? "We couldn't find a match with the current search and filter criteria."
                  : "You do not have any records in this hosted zone. Create a record to start routing traffic."}
              </Box>
              {!search && !recordType && (
                <Button
                  variant="primary"
                  onClick={() =>
                    router.push(
                      `/route53/hosted-zones/${zoneId}/records/create`,
                    )
                  }
                >
                  Create record
                </Button>
              )}
            </SpaceBetween>
          </Box>
        }
      />
      </div>
      <aside className="aws-selection-pane" aria-label="Record selection details">
        <Header variant="h2">{selected.length} {selected.length === 1 ? "record" : "records"} selected</Header>
        {selected[0] ? (
          <SpaceBetween size="m">
            <div><Box variant="awsui-key-label">Record name</Box><Link href={`/route53/hosted-zones/${zoneId}/records/${selected[0].id}`}>{selected[0].fqdn}</Link></div>
            <div><Box variant="awsui-key-label">Type</Box>{selected[0].record_type}</div>
            <div><Box variant="awsui-key-label">TTL</Box>{selected[0].ttl}</div>
            <div><Box variant="awsui-key-label">Routing policy</Box>Simple</div>
            <div><Box variant="awsui-key-label">Values</Box><Values values={selected[0].values} /></div>
            <Button onClick={() => router.push(`/route53/hosted-zones/${zoneId}/records/${selected[0].id}`)}>View details</Button>
            <Button onClick={() => router.push(`/route53/hosted-zones/${zoneId}/records/${selected[0].id}/edit`)}>Edit record</Button>
          </SpaceBetween>
        ) : <Box color="text-body-secondary">Select a record to see its details</Box>}
      </aside>
      </div>
      <DeleteRecordModal
        record={selected[0] ?? null}
        visible={deleteVisible}
        onDismiss={() => setDeleteVisible(false)}
        onDeleted={() => {
          setDeleteVisible(false);
          setSelected([]);
          if (items.length === 1 && page > 1) {
            updateUrl({ page: String(page - 1) });
          }
        }}
      />
    </SpaceBetween>
  );
}
