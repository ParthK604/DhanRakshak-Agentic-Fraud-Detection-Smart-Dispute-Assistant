import type { components, paths } from "./api-types";

export type Transaction = components["schemas"]["Transaction"];
export type RiskAssessment = components["schemas"]["RiskAssessment"];
export type RiskSummary = components["schemas"]["RiskSummary"];
export type DisputeRecord = components["schemas"]["DisputeRecord"];
export type DisputeSummary = components["schemas"]["DisputeSummary"];
export type TrustAssessment = components["schemas"]["TrustAssessment"];
export type MerchantSummary = components["schemas"]["MerchantSummary"];
export type PrecheckResponse = components["schemas"]["PrecheckResponse"];
export type ChatResponse = components["schemas"]["ChatResponse"];

export const demoUserId = process.env.NEXT_PUBLIC_DEMO_USER_ID ?? "demo-user-1";
const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly detail: string) {
    super(detail);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15_000);
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof body.detail === "string" ? body.detail : "The API returned an unexpected error.";
      throw new ApiError(response.status, detail);
    }
    return body as T;
  } finally {
    window.clearTimeout(timeout);
  }
}

type TransactionPage = paths["/api/transactions"]["get"]["responses"]["200"]["content"]["application/json"];
type RiskPage = paths["/api/risk/scores"]["get"]["responses"]["200"]["content"]["application/json"];
export type Health = {
  status: string;
  groq_model?: string;
  services?: Record<string, { ok: boolean; detail?: string | null }>;
};
type MerchantPage = paths["/api/merchants"]["get"]["responses"]["200"]["content"]["application/json"];

export const api = {
  health: () => request<Health>("/api/health"),
  transactions: (params: URLSearchParams) => request<TransactionPage>(`/api/transactions?${params}`),
  riskScores: (params: URLSearchParams) => request<RiskPage>(`/api/risk/scores?${params}`),
  riskSummary: () => request<RiskSummary>(`/api/risk/summary?user_id=${encodeURIComponent(demoUserId)}`),
  disputes: () => request<paths["/api/disputes"]["get"]["responses"]["200"]["content"]["application/json"]>(`/api/disputes?user_id=${encodeURIComponent(demoUserId)}`),
  disputeSummary: () => request<DisputeSummary>("/api/disputes/summary"),
  merchants: (params = "") => request<MerchantPage>(`/api/merchants${params ? `?${params}` : ""}`),
  merchantSummary: () => request<MerchantSummary>("/api/merchants/summary"),
  merchantTrust: (body: { merchant_name: string; merchant_url?: string; refresh?: boolean }) =>
    request<TrustAssessment>("/api/merchants/trust", { method: "POST", body: JSON.stringify(body) }),
  precheck: (body: components["schemas"]["PrecheckRequest"]) =>
    request<PrecheckResponse>("/api/merchants/precheck", { method: "POST", body: JSON.stringify(body) }),
  score: (txnId: string, force = false) =>
    request<RiskAssessment>("/api/risk/score", { method: "POST", body: JSON.stringify({ txn_id: txnId, force }) }),
  scoreIncoming: (body: components["schemas"]["IncomingTransaction"]) =>
    request<RiskAssessment>("/api/risk/score-transaction", { method: "POST", body: JSON.stringify(body) }),
  sync: () => request<components["schemas"]["SyncResult"]>("/api/transactions/sync", { method: "POST" }),
  chat: (body: components["schemas"]["ChatRequest"]) =>
    request<ChatResponse>("/api/disputes/chat", { method: "POST", body: JSON.stringify(body) }),
};
