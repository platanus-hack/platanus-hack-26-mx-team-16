"use client";

import { useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { useProcessRecordsInfiniteQuery } from "@/src/application/hooks/queries/usage";
import { useInfiniteScroll } from "@/src/application/hooks/use-infinite-scroll";
import type { ProcessRecord } from "@/src/domain/entities/usage";
import { DateRangeFilter } from "@/src/presentation/components/filters/date-range-filter";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/src/presentation/components/ui/table";

function shortDigest(digest: string): string {
  return digest.length > 16
    ? `${digest.slice(0, 8)}…${digest.slice(-8)}`
    : digest;
}

export function ProcessRecordsTable() {
  const t = useTranslations("ProcessRecordsTable");
  const locale = useLocale();
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const formatDate = (iso: string): string =>
    new Date(iso).toLocaleString(locale === "es" ? "es-MX" : "en-US", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  const activeFilters = useMemo(
    () => ({
      fromDt: dateFrom ? `${dateFrom}T00:00` : undefined,
      toDt: dateTo ? `${dateTo}T23:59` : undefined,
    }),
    [dateFrom, dateTo],
  );

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
  } = useProcessRecordsInfiniteQuery(activeFilters);

  const records = useMemo(
    () => data?.pages.flatMap((p) => p.data) ?? [],
    [data],
  );

  const scrollRef = useInfiniteScroll(
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  );

  const isInitialLoading = isFetching && records.length === 0;

  return (
    <Card className="flex flex-col flex-1 min-h-0">
      <CardHeader className="space-y-3 shrink-0">
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>

        <div className="flex flex-wrap items-center gap-3">
          <DateRangeFilter
            dateFrom={dateFrom}
            dateTo={dateTo}
            onDateFromChange={setDateFrom}
            onDateToChange={setDateTo}
          />
        </div>
      </CardHeader>

      <CardContent className="p-0 flex flex-col flex-1 min-h-0">
        <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("columns.workflow")}</TableHead>
                <TableHead>{t("columns.document")}</TableHead>
                <TableHead className="text-right">
                  {t("columns.pages")}
                </TableHead>
                <TableHead>{t("columns.processedAt")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <ProcessRecordsRows
                records={records}
                isInitialLoading={isInitialLoading}
                isFetchingNextPage={isFetchingNextPage}
                noRecordsLabel={t("noRecords")}
                formatDate={formatDate}
              />
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

interface ProcessRecordsRowsProps {
  records: ProcessRecord[];
  isInitialLoading: boolean;
  isFetchingNextPage: boolean;
  noRecordsLabel: string;
  formatDate: (iso: string) => string;
}

function ProcessRecordsRows({
  records,
  isInitialLoading,
  isFetchingNextPage,
  noRecordsLabel,
  formatDate,
}: ProcessRecordsRowsProps) {
  if (isInitialLoading) {
    return (
      <>
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonRow key={i} />
        ))}
      </>
    );
  }

  if (records.length === 0) {
    return (
      <TableRow>
        <TableCell
          colSpan={4}
          className="py-10 text-center text-sm text-muted-foreground"
        >
          {noRecordsLabel}
        </TableCell>
      </TableRow>
    );
  }

  return (
    <>
      {records.map((record) => (
        <TableRow key={record.uuid}>
          <TableCell className="text-sm">
            {record.workflowName ?? "—"}
          </TableCell>
          <TableCell className="font-mono text-xs text-muted-foreground">
            {shortDigest(record.objectKeyDigest)}
          </TableCell>
          <TableCell className="text-right tabular-nums">
            {record.pageCount}
          </TableCell>
          <TableCell className="text-sm text-muted-foreground">
            {formatDate(record.processedAt)}
          </TableCell>
        </TableRow>
      ))}
      {isFetchingNextPage && <SkeletonRow />}
    </>
  );
}

function SkeletonRow() {
  return (
    <TableRow>
      <TableCell>
        <Skeleton className="h-4 w-28" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-4 w-36" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-4 w-8 ml-auto" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-4 w-32" />
      </TableCell>
    </TableRow>
  );
}
