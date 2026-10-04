import type { CashPosition, Forecast, ImportRun } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
export const DEMO_WORKSPACE_ID = "workspace-demo";
export const DEMO_USER_ID = "user-demo-admin";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "X-User-ID": DEMO_USER_ID,
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
