"use client";

import Box from "@cloudscape-design/components/box";
import Button from "@cloudscape-design/components/button";
import Header from "@cloudscape-design/components/header";
import Link from "@cloudscape-design/components/link";
import Pagination from "@cloudscape-design/components/pagination";
import Select, { type SelectProps } from "@cloudscape-design/components/select";
import SpaceBetween from "@cloudscape-design/components/space-between";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
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
        cell: (item) => (
          <StatusIndicator type={item.type === "PUBLIC" ? "success" : "info"}>
            {item.type === "PUBLIC" ? "Public" : "Private"}
          </StatusIndicator>
        ),
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
      { id: "id", header: "Hosted Zone ID", cell: (item) => item.id },
    ],
    [],
  );

  return (
    <SpaceBetween size="l">
      {query.error && (
        <ResourceError
          error={query.error}
          retry={() => query.refetch()}
          resource="Hosted zones"
        />
      )}
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
            description="Create and manage public and private DNS namespaces."
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  disabled={selectedItems.length !== 1}
                  onClick={() => setDeleteVisible(true)}
                >
                  Delete
                </Button>
                <Button
                  variant="primary"
                  onClick={() => router.push("/route53/hosted-zones/create")}
                >
                  Create hosted zone
                </Button>
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
          </SpaceBetween>
        }
        pagination={
          <Pagination
            currentPageIndex={page}
            pagesCount={Math.max(1, pagination?.pages ?? 1)}
            onChange={({ detail }) =>
              updateUrl({ page: detail.currentPageIndex === 1 ? undefined : String(detail.currentPageIndex) })
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
                  ? "Adjust or clear your search and filters."
                  : "Create a hosted zone to begin managing DNS records."}
              </Box>
              {!search && !type && (
                <Button onClick={() => router.push("/route53/hosted-zones/create")}>
                  Create hosted zone
                </Button>
              )}
            </SpaceBetween>
          </Box>
        }
      />
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
