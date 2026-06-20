"use client";

import { AlertCircle, CheckCircle2, Clock, FileText } from "lucide-react";

import { useDashboardProcessing } from "@/src/application/hooks/queries/dashboard";
import type {
  LiveProcessingDocument,
  PipelineStage,
  ProcessingSummary,
} from "@/src/domain/entities/dashboard/processing";
import { PipelineStageKey } from "@/src/domain/entities/dashboard/processing";
import { Badge } from "@/src/presentation/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
import { Spinner } from "@/src/presentation/components/ui/spinner";

// Per-stage bar colours. PROCESSING is the v1 fallback bucket (workers
// not writing `processing_status` yet) — same colour as OCR so it reads
// like an in-flight stage.
const STAGE_COLORS: Record<string, string> = {
  [PipelineStageKey.UPLOAD]: "bg-blue-500",
  [PipelineStageKey.OCR]: "bg-purple-500",
  [PipelineStageKey.EXTRACTION]: "bg-yellow-500",
  [PipelineStageKey.VALIDATION]: "bg-orange-500",
  [PipelineStageKey.PROCESSING]: "bg-purple-500",
  [PipelineStageKey.COMPLETE]: "bg-green-500",
};

function formatAvgProcessingTime(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = seconds / 60;
  return `${minutes.toFixed(1)}m`;
}

function formatEta(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${seconds}s`;
  return `${Math.round(seconds / 60)}min`;
}

export function ProcessingTab() {
  const { data, isLoading, isError } = useDashboardProcessing();

  if (isLoading && !data) return <ProcessingTabSkeleton />;
  if (isError || !data) return <ProcessingTabError />;

  return (
    <div className="space-y-4">
      <SummaryCards summary={data.summary} />

      <div className="grid gap-4 md:grid-cols-2">
        <PipelineStagesCard stages={data.stages} />
        <LiveProcessingCard documents={data.liveProcessing} />
      </div>
    </div>
  );
}

function SummaryCards({ summary }: { summary: ProcessingSummary }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      <StatCard
        title="In Queue"
        value={summary.inQueue}
        subtitle="Waiting to process"
        icon={<Clock className="h-4 w-4 text-muted-foreground" />}
      />
      <StatCard
        title="Processing"
        value={summary.processing}
        subtitle="Active now"
        icon={<Spinner size="sm" variant="muted" />}
      />
      <StatCard
        title="Completed"
        value={summary.completedToday}
        subtitle="Today"
        icon={<CheckCircle2 className="h-4 w-4 text-muted-foreground" />}
      />
      <StatCard
        title="Failed"
        value={summary.failed}
        subtitle="Needs review"
        icon={<AlertCircle className="h-4 w-4 text-muted-foreground" />}
      />
      <StatCard
        title="Avg Time"
        value={formatAvgProcessingTime(summary.avgProcessingSeconds)}
        subtitle="Per document"
        icon={<FileText className="h-4 w-4 text-muted-foreground" />}
      />
    </div>
  );
}

function StatCard({
  title,
  value,
  subtitle,
  icon,
}: {
  title: string;
  value: number | string;
  subtitle: string;
  icon: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </CardContent>
    </Card>
  );
}

function PipelineStagesCard({ stages }: { stages: PipelineStage[] }) {
  const total = stages.reduce((acc, s) => acc + s.count, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Stages</CardTitle>
        <CardDescription>Documents distribution across stages</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {stages.length === 0 ? (
          <p className="text-sm text-muted-foreground">No documents yet.</p>
        ) : (
          stages.map((stage) => (
            <div key={stage.stage} className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{stage.label}</span>
                <span className="text-muted-foreground">{stage.count} docs</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full ${STAGE_COLORS[stage.stage] ?? "bg-primary"}`}
                  style={{
                    width: total > 0 ? `${(stage.count / total) * 100}%` : "0%",
                  }}
                />
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function LiveProcessingCard({
  documents,
}: {
  documents: LiveProcessingDocument[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Live Processing</CardTitle>
        <CardDescription>Currently processing documents</CardDescription>
      </CardHeader>
      <CardContent>
        {documents.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No documents are being processed right now.
          </p>
        ) : (
          <div className="space-y-4">
            {documents.map((doc) => (
              <div key={doc.uuid} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{doc.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {doc.stage}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatEta(doc.etaSeconds)}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${doc.progressPct}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground w-10 text-right">
                    {doc.progressPct}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ProcessingTabSkeleton() {
  return (
    <div className="flex items-center justify-center py-16">
      <Spinner size="md" variant="muted" />
    </div>
  );
}

function ProcessingTabError() {
  return (
    <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
      Couldn't load processing data. Try refreshing the page.
    </div>
  );
}
