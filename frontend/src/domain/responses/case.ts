import type { Case, CaseDetail } from "../entities/case";

export interface CaseResponse {
  data: Case;
  datetime: string;
}

export interface CaseDetailResponse {
  data: CaseDetail;
  datetime: string;
}

export interface CaseListResponse {
  data: Case[];
  datetime: string;
}
