export interface CreditBalance {
  credits: number;
  expiresAt: string;
}

export interface Invoice {
  uuid: string;
  amount: number;
  credits: number;
  status: "paid" | "pending" | "failed";
  date: string;
  downloadUrl?: string;
}
