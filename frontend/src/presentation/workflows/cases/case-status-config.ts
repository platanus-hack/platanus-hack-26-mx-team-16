import {
  AlertTriangle,
  Archive,
  CheckCircle2,
  Clock,
  Eye,
  Inbox,
  MessageCircleQuestion,
  Sparkles,
  Users,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { CaseStatus } from "@/src/domain/entities/case";

export type CaseStatusVariant =
  | "default"
  | "secondary"
  | "outline"
  | "destructive";

/**
 * E4 · Badges para la máquina de estados pública del caso (11 estados).
 * Paleta near-flat sobre grises fríos: tintes suaves + texto profundo,
 * un icono por estado. Labels en español (producto es-first).
 */
export const caseStatusConfig: Record<
  CaseStatus,
  {
    label: string;
    variant: CaseStatusVariant;
    icon: LucideIcon;
    className: string;
  }
> = {
  [CaseStatus.RECEIVING]: {
    label: "Recibiendo",
    variant: "outline",
    icon: Inbox,
    className:
      "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/60 dark:text-slate-200 dark:border-slate-700",
  },
  [CaseStatus.PROCESSING]: {
    label: "Procesando",
    variant: "default",
    icon: Clock,
    className:
      "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/40 dark:text-blue-200 dark:border-blue-800",
  },
  [CaseStatus.NEEDS_CLARIFICATION]: {
    label: "Requiere aclaración",
    variant: "outline",
    icon: MessageCircleQuestion,
    className:
      "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/40 dark:text-amber-200 dark:border-amber-800",
  },
  [CaseStatus.NEEDS_REVIEW]: {
    label: "Requiere revisión",
    variant: "outline",
    icon: Eye,
    className:
      "bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-900/40 dark:text-violet-200 dark:border-violet-800",
  },
  [CaseStatus.ANALYZING]: {
    label: "Analizando",
    variant: "default",
    icon: Sparkles,
    className:
      "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/40 dark:text-blue-200 dark:border-blue-800",
  },
  [CaseStatus.REVIEW_L1]: {
    label: "Revisión L1",
    variant: "outline",
    icon: Users,
    className:
      "bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-900/40 dark:text-violet-200 dark:border-violet-800",
  },
  [CaseStatus.REVIEW_L2]: {
    label: "Revisión L2",
    variant: "outline",
    icon: Users,
    className:
      "bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-900/40 dark:text-violet-200 dark:border-violet-800",
  },
  [CaseStatus.COMPLETED]: {
    label: "Completado",
    variant: "secondary",
    icon: CheckCircle2,
    className:
      "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-200 dark:border-emerald-800",
  },
  [CaseStatus.REJECTED]: {
    label: "Rechazado",
    variant: "destructive",
    icon: XCircle,
    className:
      "bg-red-100 text-red-700 border-red-200 dark:bg-red-900/40 dark:text-red-200 dark:border-red-800",
  },
  [CaseStatus.FAILED]: {
    label: "Fallido",
    variant: "destructive",
    icon: AlertTriangle,
    className:
      "bg-red-100 text-red-700 border-red-200 dark:bg-red-900/40 dark:text-red-200 dark:border-red-800",
  },
  [CaseStatus.ARCHIVED]: {
    label: "Archivado",
    variant: "outline",
    icon: Archive,
    className:
      "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/40 dark:text-amber-200 dark:border-amber-800",
  },
};
