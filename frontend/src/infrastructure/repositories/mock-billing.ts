import type { CreditBalance, Invoice } from "@/src/domain/entities/billing";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { BillingRepository } from "@/src/domain/repositories/billing";
import type {
  CreditBalanceResponse,
  InvoiceListResponse,
  BillingDataResponse,
} from "@/src/domain/responses/billing";

const mockCreditBalance: CreditBalance = {
  credits: 200,
  expiresAt: new Date("2025-02-03").toISOString(),
};

const mockInvoices: Invoice[] = [];

export class MockBillingRepository implements BillingRepository {
  private creditBalance: CreditBalance = { ...mockCreditBalance };
  private invoices: Invoice[] = [...mockInvoices];

  async getBillingData(): Promise<BillingDataResponse | ErrorFeeback> {
    return {
      creditBalance: this.creditBalance,
      invoices: this.invoices,
      datetime: new Date().toISOString(),
    };
  }

  async getCreditBalance(): Promise<CreditBalanceResponse | ErrorFeeback> {
    return {
      data: this.creditBalance,
      datetime: new Date().toISOString(),
    };
  }

  async getInvoices(): Promise<InvoiceListResponse | ErrorFeeback> {
    return {
      data: this.invoices,
      datetime: new Date().toISOString(),
    };
  }

  async buyCredits(
    amount: number
  ): Promise<CreditBalanceResponse | ErrorFeeback> {
    // Simulate buying credits
    this.creditBalance.credits += amount;

    // Create a new invoice
    const newInvoice: Invoice = {
      uuid: `inv-${Date.now()}`,
      amount: amount * 0.01, // $0.01 per credit
      credits: amount,
      status: "paid",
      date: new Date().toISOString(),
      downloadUrl: `/invoices/inv-${Date.now()}.pdf`,
    };

    this.invoices.unshift(newInvoice);

    return {
      data: this.creditBalance,
      datetime: new Date().toISOString(),
    };
  }
}
