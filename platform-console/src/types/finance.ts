export type InvoiceStatus =
  | "draft"
  | "issued"
  | "partially_paid"
  | "paid"
  | "overdue"
  | "void";

export type PaymentStatus = "pending" | "completed" | "failed" | "cancelled";

export interface Invoice {
  id: string;
  tenant_id: string;
  party_id: string;
  work_item_id: string | null;
  document_id: string | null;
  invoice_number: string;
  status: InvoiceStatus;
  currency: string;
  subtotal: string;
  tax_amount: string;
  total: string;
  amount_paid: string;
  balance_due: string;
  issue_date: string | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface Payment {
  id: string;
  tenant_id: string;
  party_id: string | null;
  payment_number: string;
  amount: string;
  currency: string;
  amount_allocated: string;
  unallocated_amount: string;
  payment_date: string;
  method: string;
  status: PaymentStatus;
  reference_number: string | null;
  created_at: string;
  updated_at: string;
}

export interface Receivable {
  invoice_id: string;
  invoice_number: string;
  party_id: string;
  status: InvoiceStatus;
  currency: string;
  total: string;
  amount_paid: string;
  balance_due: string;
  due_date: string | null;
  is_overdue: boolean;
}

export interface FinanceSummary {
  currency: string;
  total_invoiced: string;
  total_paid: string;
  total_outstanding: string;
  open_invoices_count: number;
  overdue_invoices_count: number;
  overdue_amount: string;
}

export interface ListInvoicesParams {
  status?: InvoiceStatus;
  party_id?: string;
  skip?: number;
  limit?: number;
}

export interface ListPaymentsParams {
  status?: PaymentStatus;
  party_id?: string;
  skip?: number;
  limit?: number;
}
