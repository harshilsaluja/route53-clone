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
import { Suspense, useEffect, useMemo, useState } from "react";
import { DeleteZoneModal } from "@/components/delete-zone-modal";
import { LoadingScreen } from "@/components/loading-screen";
import { ResourceError } from "@/components/resource-error";
import { listHostedZones } from "@/services/hosted-zones";
import type { HostedZone, HostedZoneType } from "@/types/api";

const typeOptions: SelectProps.Option[] = [
  { label: "All types", value: "ALL" },
  { label: "Public", value: "PUBLIC" },
  { label: "Private", value: "PRIVATE" },
];

function HostedZonesList() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const search = searchParams.get("search") ?? "";
  const typeValue = searchParams.get("type");
  const type =
    typeValue === "PUBLIC" || typeValue === "PRIVATE" ? typeValue : undefined;
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const [searchText, setSearchText] = useState(search);
  const [selectedItems, setSelectedItems] = useState<HostedZone[]>([]);
  const [deleteVisible, setDeleteVisible] = useState(false);

  const updateUrl = (updates: Record<string, string | undefined>) => {
    const next = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    router.replace(`/route53/hosted-zones?${next.toString()}`);
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
    queryKey: ["hosted-zones", { search, type, page, pageSize: 20 }],
    queryFn: ({ signal }) =>
      listHostedZones(
        { search, type: type as HostedZoneType | undefined, page, page_size: 20 },
        signal,
      ),
    placeholderData: keepPreviousData,
  });
  const items = query.data?.items ?? [];
  const pagination = query.data?.pagination;
  const columns = useMemo<TableProps.ColumnDefinition<HostedZone>[]>(
    () => [
      {
        id: "name",
        header: "Domain name",
        cell: (item) => (
          <Link href={`/route53/hosted-zones/${item.id}`} fontSize="body-m">
            {item.name}
          </Link>
        ),
      },
      {
        id: "type",
        header: "Type",
        cell: (item) => (item.type === "PUBLIC" ? "Public" : "Private"),
      },
      {
        id: "records",
        header: "Record count",
        cell: (item) => item.record_count,
      },
      {
        id: "description",
        header: "Description",
        cell: (item) => item.comment || "—",
      },
      { id: "id", header: "Hosted zone ID", cell: (item) => item.id },
    ],
    [],
  );

  return (
    <SpaceBetween size="m">
      {query.error && (
        <ResourceError
          error={query.error}
          retry={() => query.refetch()}
          resource="Hosted zones"
        />
      )}
      <div className="aws-resource-split">
      <div className="aws-console-table">
      <Table
        items={items}
        columnDefinitions={columns}
        trackBy="id"
        selectionType="single"
        selectedItems={selectedItems}
        onSelectionChange={({ detail }) => setSelectedItems(detail.selectedItems)}
        loading={query.isPending || query.isFetching}
        loadingText="Loading hosted zones"
        header={
          <Header
            variant="h1"
            counter={pagination ? `(${pagination.total})` : undefined}
            description="A hosted zone tells Route 53 how to respond to DNS queries for a domain."
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button iconName="refresh" ariaLabel="Refresh hosted zones" onClick={() => query.refetch()} />
                <Button
                  disabled={selectedItems.length !== 1}
                  onClick={() => selectedItems[0] && router.push(`/route53/hosted-zones/${selectedItems[0].id}`)}
                >
                  View details
                </Button>
                <Button
                  disabled={selectedItems.length !== 1}
                  onClick={() => selectedItems[0] && router.push(`/route53/hosted-zones/${selectedItems[0].id}/edit`)}
                >
                  Edit
                </Button>
                <Button
                  disabled={selectedItems.length !== 1}
                  onClick={() => setDeleteVisible(true)}
                >
                  Delete
                </Button>
                <span className="aws-create-action"><Button
                    variant="primary"
                    onClick={() => router.push("/route53/hosted-zones/create")}
                  >Create hosted zone</Button></span>
              </SpaceBetween>
            }
          >
            Hosted zones
          </Header>
        }
        filter={
          <SpaceBetween direction="horizontal" size="s">
            <TextFilter
              filteringText={searchText}
              filteringPlaceholder="Find hosted zones"
              filteringAriaLabel="Find hosted zones"
              countText={
                pagination
                  ? `${pagination.total} ${pagination.total === 1 ? "match" : "matches"}`
                  : undefined
              }
              onChange={({ detail }) => setSearchText(detail.filteringText)}
            />
            <div className="filter-select-wrapper">
              <Select
                ariaLabel="Filter by hosted zone type"
                selectedOption={
                  typeOptions.find((option) => option.value === (type ?? "ALL")) ??
                  typeOptions[0]
                }
                options={typeOptions}
                onChange={({ detail }) =>
                  updateUrl({
                    type:
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
              <b>{search || type ? "No matching hosted zones" : "No hosted zones"}</b>
              <Box color="text-body-secondary">
                {search || type
                  ? "We couldn't find a match with the current search and filter criteria."
                  : "You do not have any hosted zones. Create a hosted zone to start routing traffic."}
              </Box>
              {!search && !type && (
                <Button
                  variant="primary"
                  onClick={() => router.push("/route53/hosted-zones/create")}
                >
                  Create hosted zone
                </Button>
              )}
            </SpaceBetween>
          </Box>
        }
      />
      </div>
      <aside className="aws-selection-pane" aria-label="Hosted zone selection details">
        <Header variant="h2">{selectedItems.length} hosted zone selected</Header>
        {selectedItems[0] ? (
          <SpaceBetween size="m">
            <div><Box variant="awsui-key-label">Domain name</Box><Link href={`/route53/hosted-zones/${selectedItems[0].id}`}>{selectedItems[0].name}</Link></div>
            <div><Box variant="awsui-key-label">Type</Box>{selectedItems[0].type === "PUBLIC" ? "Public" : "Private"}</div>
            <div><Box variant="awsui-key-label">Record count</Box>{selectedItems[0].record_count}</div>
            <div><Box variant="awsui-key-label">Description</Box>{selectedItems[0].comment || "—"}</div>
          </SpaceBetween>
        ) : <Box color="text-body-secondary">Select a hosted zone to see its details</Box>}
      </aside>
      </div>
      <DeleteZoneModal
        zone={selectedItems[0] ?? null}
        visible={deleteVisible}
        onDismiss={() => setDeleteVisible(false)}
        onDeleted={() => {
          setDeleteVisible(false);
          setSelectedItems([]);
          if (items.length === 1 && page > 1) {
            updateUrl({ page: String(page - 1) });
          }
        }}
      />
    </SpaceBetween>
  );
}

export default function HostedZonesPage() {
  return (
    <Suspense fallback={<LoadingScreen label="Loading hosted zones" />}>
      <HostedZonesList />
    </Suspense>
  );
}
