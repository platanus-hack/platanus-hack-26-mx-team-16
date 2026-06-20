import type { CreditBalance, Invoice } from "@/src/domain/entities/billing";

export interface CreditBalanceResponse {
  data: CreditBalance;
  datetime: string;
}

export interface InvoiceListResponse {
  data: Invoice[];
  datetime: string;
}

export interface BillingDataResponse {
  creditBalance: CreditBalance;
  invoices: Invoice[];
  datetime: string;
}
