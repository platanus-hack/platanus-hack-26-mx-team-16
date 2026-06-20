import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type {
  CreditBalanceResponse,
  InvoiceListResponse,
  BillingDataResponse,
} from "@/src/domain/responses/billing";

export interface BillingRepository {
  getBillingData(): Promise<BillingDataResponse | ErrorFeeback>;

  getCreditBalance(): Promise<CreditBalanceResponse | ErrorFeeback>;

  getInvoices(): Promise<InvoiceListResponse | ErrorFeeback>;

  buyCredits(amount: number): Promise<CreditBalanceResponse | ErrorFeeback>;
}
