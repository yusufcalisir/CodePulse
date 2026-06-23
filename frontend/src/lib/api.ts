/**
 * CodePulse API client — communicates with the FastAPI backend.
 */

import type {
  Anomaly,
  CycleTimeResponse,
  Insight,
  InsightsResponse,
  OverviewResponse,
  Repository,
  RepositoryListResponse,
  ReviewLatencyResponse,
  SyncStatusResponse,
  ThroughputResponse,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Org-Id": "default_org",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }

  return res.json();
}

// ── Repository endpoints ────────────────────────────────────

export async function getRepositories(): Promise<Repository[]> {
  const data = await fetchApi<RepositoryListResponse>("/repos");
  return data.repositories;
}

export async function getRepository(id: number): Promise<Repository> {
  return fetchApi<Repository>(`/repos/${id}`);
}

export async function syncRepository(
  fullName: string,
): Promise<{ message: string; full_name: string; status: string }> {
  return fetchApi("/repos/sync", {
    method: "POST",
    body: JSON.stringify({ full_name: fullName }),
  });
}

export async function getSyncStatus(repoId: number): Promise<SyncStatusResponse> {
  return fetchApi<SyncStatusResponse>(`/repos/${repoId}/sync-status`);
}

// ── Metrics endpoints ───────────────────────────────────────

export async function getOverview(repoId: number): Promise<OverviewResponse> {
  return fetchApi<OverviewResponse>(`/metrics/overview?repo_id=${repoId}`);
}

export async function getCycleTime(
  repoId: number,
  days = 30,
): Promise<CycleTimeResponse> {
  return fetchApi<CycleTimeResponse>(
    `/metrics/pr-cycle-time?repo_id=${repoId}&days=${days}`,
  );
}

export async function getReviewLatency(
  repoId: number,
  days = 30,
): Promise<ReviewLatencyResponse> {
  return fetchApi<ReviewLatencyResponse>(
    `/metrics/review-latency?repo_id=${repoId}&days=${days}`,
  );
}

export async function getThroughput(
  repoId: number,
  weeks = 12,
): Promise<ThroughputResponse> {
  return fetchApi<ThroughputResponse>(
    `/metrics/throughput?repo_id=${repoId}&weeks=${weeks}`,
  );
}

// ── Insights endpoint ───────────────────────────────────────

export async function getInsights(repoId: number): Promise<InsightsResponse> {
  return fetchApi<InsightsResponse>(`/metrics/insights?repo_id=${repoId}`);
}

// ── Anomalies endpoint ──────────────────────────────────────

export async function getAnomalies(
  repoId: number,
  days = 30,
): Promise<Anomaly[]> {
  return fetchApi<Anomaly[]>(`/anomalies?repo_id=${repoId}&days=${days}`);
}
