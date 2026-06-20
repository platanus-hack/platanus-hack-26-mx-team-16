import { FileText, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { CaseDocumentStatus } from "@/src/domain/entities/case";

export const docStatusConfig: Record<
  CaseDocumentStatus,
  {
    label: string;
    variant: "default" | "secondary" | "outline" | "destructive";
    icon: typeof FileText;
  }
> = {
  [CaseDocumentStatus.EMPTY]: {
    label: "Vacío",
    variant: "secondary",
    icon: FileText,
  },
  [CaseDocumentStatus.UPLOADED]: {
    label: "Subido",
    variant: "default",
    icon: FileText,
  },
  [CaseDocumentStatus.PROCESSING]: {
    label: "Procesando",
    variant: "outline",
    icon: Clock,
  },
  [CaseDocumentStatus.EXTRACTED]: {
    label: "Extraído",
    variant: "default",
    icon: CheckCircle2,
  },
  [CaseDocumentStatus.ERROR]: {
    label: "Error",
    variant: "destructive",
    icon: AlertCircle,
  },
};
