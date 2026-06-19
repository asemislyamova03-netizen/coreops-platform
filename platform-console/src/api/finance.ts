import type {
  FinanceSummary,
  Invoice,
  ListInvoicesParams,
  ListPaymentsParams,
  Payment,
  Receivable,
} from "../types/finance";
import { buildQuery } from "./query";
import { workspaceApiFetch } from "./workspace";

export function getFinanceSummary(currency = "RUB"): Promise<FinanceSummary> {
  return workspaceApiFetch<FinanceSummary>(`/finance/summary${buildQuery({ currency })}`);
}

export function listReceivables(): Promise<Receivable[]> {
  return workspaceApiFetch<Receivable[]>("/finance/receivables");
}

export function listInvoices(params: ListInvoicesParams = {}): Promise<Invoice[]> {
  return workspaceApiFetch<Invoice[]>(
    `/finance/invoices${buildQuery({
      status: params.status,
      party_id: params.party_id,
      skip: params.skip,
      limit: params.limit,
    })}`,
  );
}

export function listPayments(params: ListPaymentsParams = {}): Promise<Payment[]> {
  return workspaceApiFetch<Payment[]>(
    `/finance/payments${buildQuery({
      status: params.status,
      party_id: params.party_id,
      skip: params.skip,
      limit: params.limit,
    })}`,
  );
}
