import type {
  CashPosition,
  DailyBrief,
  Forecast,
  ImportRun,
  Payment,
  PaymentAuditEvent,
  PaymentCreateInput,
  PaymentProfile,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
export const DEMO_WORKSPACE_ID = "workspace-demo";
export const DEMO_USER_ID = "user-demo-admin";
export const DEMO_PREPARER_USER_ID = "user-demo-preparer";
export const DEMO_APPROVER_USER_ID = "user-demo-approver";

async function request<T>(
  path: string,
  init?: RequestInit,
  actorUserId = DEMO_USER_ID,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "X-User-ID": actorUserId,
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // The default message remains useful when an upstream returns no JSON.
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function getCashPosition(): Promise<CashPosition> {
  return request(`/api/workspaces/${DEMO_WORKSPACE_ID}/cash-position`);
}

export function getImportHistory(): Promise<ImportRun[]> {
  return request(`/api/workspaces/${DEMO_WORKSPACE_ID}/imports`);
}

export function uploadBankCsv(file: File): Promise<ImportRun> {
  const form = new FormData();
  form.append("file", file);
  return request(`/api/workspaces/${DEMO_WORKSPACE_ID}/imports/bank-csv`, {
    method: "POST",
    body: form,
  });
}

export function runForecast(): Promise<Forecast> {
  return request(`/api/workspaces/${DEMO_WORKSPACE_ID}/forecasts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ horizon_days: 90 }),
  });
}

export function runDailyBrief(): Promise<DailyBrief> {
  return request(`/api/workspaces/${DEMO_WORKSPACE_ID}/daily-briefs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function getPaymentProfiles(): Promise<PaymentProfile[]> {
  return request(`/api/workspaces/${DEMO_WORKSPACE_ID}/payment-profiles`);
}

export function getPayments(): Promise<Payment[]> {
  return request(`/api/workspaces/${DEMO_WORKSPACE_ID}/payments`);
}

export function preparePayment(input: PaymentCreateInput): Promise<Payment> {
  return request(
    `/api/workspaces/${DEMO_WORKSPACE_ID}/payments`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
    DEMO_PREPARER_USER_ID,
  );
}

export function submitPayment(paymentId: string): Promise<Payment> {
  return request(
    `/api/workspaces/${DEMO_WORKSPACE_ID}/payments/${paymentId}/submit`,
    { method: "POST" },
    DEMO_PREPARER_USER_ID,
  );
}

export function decidePayment(
  paymentId: string,
  decision: "approve" | "reject",
  comment: string,
): Promise<Payment> {
  return request(
    `/api/workspaces/${DEMO_WORKSPACE_ID}/payments/${paymentId}/${decision}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ comment }),
    },
    DEMO_APPROVER_USER_ID,
  );
}

export function getPaymentAudit(paymentId: string): Promise<PaymentAuditEvent[]> {
  return request(`/api/workspaces/${DEMO_WORKSPACE_ID}/payments/${paymentId}/audit-events`);
}

export async function downloadPaymentXml(paymentId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/workspaces/${DEMO_WORKSPACE_ID}/payments/${paymentId}/iso20022`,
    { headers: { "X-User-ID": DEMO_PREPARER_USER_ID } },
  );
  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // Keep the status-based fallback when no JSON error body is available.
    }
    throw new Error(message);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `payment-${paymentId}.xml`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
