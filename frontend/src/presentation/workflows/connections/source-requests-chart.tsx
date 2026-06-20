"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { SourceEvent } from "@/src/application/hooks/queries/sources";

const DAYS = 14;

interface DayBucket {
  key: string;
  label: string;
  total: number;
  failed: number;
  errorRate: number;
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/** Local-calendar day key (YYYY-MM-DD), so an event never lands in the wrong
 * day at the UTC/local boundary. */
function dayKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** Buckets received requests into the last {@link DAYS} days. `total` counts
 * every inbound file; `failed` counts the ones whose processing failed. */
function bucketEvents(events: SourceEvent[]): DayBucket[] {
  const today = startOfDay(new Date());
  const buckets: DayBucket[] = [];
  const byKey = new Map<string, DayBucket>();

  for (let i = DAYS - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const key = dayKey(d);
    const bucket: DayBucket = {
      key,
      label: d.toLocaleDateString(undefined, {
        month: "numeric",
        day: "numeric",
      }),
      total: 0,
      failed: 0,
      errorRate: 0,
    };
    buckets.push(bucket);
    byKey.set(key, bucket);
  }

  for (const event of events) {
    if (!event.createdAt) continue;
    const bucket = byKey.get(dayKey(new Date(event.createdAt)));
    if (!bucket) continue;
    bucket.total += 1;
    if (event.status === "FAILED") bucket.failed += 1;
  }

  for (const bucket of buckets) {
    bucket.errorRate =
      bucket.total > 0 ? Math.round((bucket.failed / bucket.total) * 100) : 0;
  }

  return buckets;
}

/** Requests-over-time charts for a webhook ingest source, mirroring
 * WebhookDeliveriesChart: received vs failed per day + the error-rate trend. */
export function SourceRequestsChart({ events }: { events: SourceEvent[] }) {
  const data = useMemo(() => bucketEvents(events), [events]);

  const totals = useMemo(() => {
    const received = events.length;
    const failed = events.filter((e) => e.status === "FAILED").length;
    const errorRate = received > 0 ? Math.round((failed / received) * 100) : 0;
    return { received, failed, errorRate };
  }, [events]);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Received requests — total vs failed per day */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="text-sm font-semibold">Peticiones recibidas</h3>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="inline-block h-2 w-2 rounded-full bg-primary" />
              Total{" "}
              <span className="font-mono font-medium text-foreground">
                {totals.received}
              </span>
            </span>
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="inline-block h-2 w-2 rounded-full bg-destructive" />
              Fallidas{" "}
              <span className="font-mono font-medium text-foreground">
                {totals.failed}
              </span>
            </span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart
            data={data}
            margin={{ top: 4, right: 8, bottom: 0, left: -20 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              className="stroke-muted"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              stroke="#888888"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              minTickGap={16}
            />
            <YAxis
              stroke="#888888"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
              width={32}
            />
            <Tooltip
              cursor={{ stroke: "var(--color-border)" }}
              contentStyle={{
                borderRadius: 8,
                border: "1px solid var(--color-border)",
                background: "var(--color-popover)",
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="total"
              name="Total"
              stroke="var(--color-primary)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="failed"
              name="Fallidas"
              stroke="var(--color-destructive)"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Error rate — % failed per day */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="text-sm font-semibold">Tasa de error</h3>
          <span className="font-mono text-xs font-medium text-foreground">
            {totals.errorRate}%
          </span>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart
            data={data}
            margin={{ top: 4, right: 8, bottom: 0, left: -20 }}
          >
            <defs>
              <linearGradient id="src-error-fill" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="var(--color-destructive)"
                  stopOpacity={0.25}
                />
                <stop
                  offset="100%"
                  stopColor="var(--color-destructive)"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              className="stroke-muted"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              stroke="#888888"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              minTickGap={16}
            />
            <YAxis
              stroke="#888888"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              width={32}
              domain={[0, 100]}
              unit="%"
            />
            <Tooltip
              cursor={{ stroke: "var(--color-border)" }}
              formatter={(value) => [`${value}%`, "Tasa de error"]}
              contentStyle={{
                borderRadius: 8,
                border: "1px solid var(--color-border)",
                background: "var(--color-popover)",
                fontSize: 12,
              }}
            />
            <Area
              type="monotone"
              dataKey="errorRate"
              name="Tasa de error"
              stroke="var(--color-destructive)"
              strokeWidth={2}
              fill="url(#src-error-fill)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
