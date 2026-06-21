/**
 * biome-ignore-all assist/source/organizeImports: barrel exports are grouped by product area for discoverability.
 *
 * Owliver design-system barrel — the stable import surface for screen agents.
 * Import components from here, e.g.:
 *   import { GradeBadge, Gauge, SeverityChip } from "@/src/presentation/owliver";
 *
 * (Deep imports also work and are equivalent; this barrel just documents the set.)
 */

// ─── Core display components (light + SOC) ───
export { GradeBadge } from "./components/grade-badge";
export type { GradeBadgeProps } from "./components/grade-badge";
export { Gauge } from "./components/gauge";
export type { GaugeProps } from "./components/gauge";
export { SeverityChip } from "./components/severity-chip";
export type { SeverityChipProps } from "./components/severity-chip";
export { StatusBadge, CoverageBadges } from "./components/status-badge";
export type {
  StatusBadgeProps,
  StatusBadgeVariant,
} from "./components/status-badge";
export { ScaleLegend } from "./components/scale-legend";
export type { ScaleLegendProps } from "./components/scale-legend";
export { ProgressBar } from "./components/progress-bar";
export type { ProgressBarProps } from "./components/progress-bar";
export { OwlMascot } from "./components/owl-mascot";
export type { OwlMascotProps, OwlState } from "./components/owl-mascot";
export { FindingFeedItem } from "./components/finding-feed-item";
export type { FindingFeedItemProps } from "./components/finding-feed-item";
export { FindingDetailDialog } from "./components/finding-detail-dialog";
export type { FindingDetailDialogProps } from "./components/finding-detail-dialog";

// ─── Theater (SOC) ───
export { ToolChip } from "./theater/tool-chip";
export type { ToolChipProps } from "./theater/tool-chip";
export { AgentLane } from "./theater/agent-lane";
export type { AgentLaneProps } from "./theater/agent-lane";
export { TheaterView } from "./theater/theater-view";
export type { TheaterViewProps } from "./theater/theater-view";
export { TheaterNotFound } from "./theater/theater-not-found";

// ─── Report (§F7/§F8 — light, two-layer) ───
export { ReportExecutive } from "./report/report-executive";
export type { ReportExecutiveProps } from "./report/report-executive";
export { ReportTechnical } from "./report/report-technical";
export type { ReportTechnicalProps } from "./report/report-technical";
export {
  FindingAccordion,
  FindingAccordionItem,
} from "./report/finding-accordion";
export type {
  FindingAccordionProps,
  FindingAccordionItemProps,
} from "./report/finding-accordion";
export { ReportActions } from "./report/report-actions";
export type { ReportActionsProps } from "./report/report-actions";

// ─── Scan form ───
export { AttestationGate } from "./scan/attestation-gate";
export type { AttestationGateProps } from "./scan/attestation-gate";
export { ScanForm } from "./scan/scan-form";
export type { ScanFormProps } from "./scan/scan-form";
export { ScanFormDialog } from "./scan/scan-form-dialog";
export type { ScanFormDialogProps } from "./scan/scan-form-dialog";

// ─── Public chrome ───
export { BrandLockup } from "./chrome/brand-lockup";
export type { BrandLockupProps } from "./chrome/brand-lockup";
export { TopNav } from "./chrome/top-nav";
export type { TopNavProps } from "./chrome/top-nav";
export { Footer } from "./chrome/footer";
export type { FooterProps } from "./chrome/footer";
