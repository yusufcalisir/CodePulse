import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getRepositories,
  getRepository,
  syncRepository,
  getSyncStatus,
  getOverview,
  getCycleTime,
  getInsights,
} from "@/lib/api";

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("CodePulse API Client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("getRepositories returns list of repositories on success", async () => {
    const mockRepos = [
      { id: 1, name: "repo1", full_name: "org/repo1" },
      { id: 2, name: "repo2", full_name: "org/repo2" },
    ];
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ repositories: mockRepos }),
    });

    const repos = await getRepositories();

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/repos",
      expect.any(Object)
    );
    expect(repos).toEqual(mockRepos);
  });

  it("getRepository returns specific repo info", async () => {
    const mockRepo = { id: 1, name: "repo1", full_name: "org/repo1" };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockRepo,
    });

    const repo = await getRepository(1);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/repos/1",
      expect.any(Object)
    );
    expect(repo).toEqual(mockRepo);
  });

  it("syncRepository posts the payload to backend", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: "Sync started", status: "running" }),
    });

    const response = await syncRepository("org/repo1");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/repos/sync",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ full_name: "org/repo1" }),
      })
    );
    expect(response.status).toBe("running");
  });

  it("getSyncStatus queries status endpoint", async () => {
    const mockStatus = { sync_id: 1, status: "completed", pr_count: 5 };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockStatus,
    });

    const status = await getSyncStatus(1);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/repos/1/sync-status",
      expect.any(Object)
    );
    expect(status).toEqual(mockStatus);
  });

  it("getOverview queries overview metrics endpoint", async () => {
    const mockOverview = { metrics: { wip: 5 }, cycle_time_trend: [] };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockOverview,
    });

    const overview = await getOverview(1);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/metrics/overview?repo_id=1",
      expect.any(Object)
    );
    expect(overview).toEqual(mockOverview);
  });

  it("getCycleTime passes correct query parameters", async () => {
    const mockCycleTime = { summary: { avg: 12 }, trend: [] };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockCycleTime,
    });

    const data = await getCycleTime(1, 90);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/metrics/pr-cycle-time?repo_id=1&days=90",
      expect.any(Object)
    );
    expect(data).toEqual(mockCycleTime);
  });

  it("getInsights queries insights endpoint and returns structured response", async () => {
    const mockInsightsResponse = {
      rule_engine: [],
      statistical_layer: [],
      llm_layer: { executive_summary: "summary", why_did_this_happen: "why" },
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockInsightsResponse,
    });

    const insights = await getInsights(1);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/metrics/insights?repo_id=1",
      expect.any(Object)
    );
    expect(insights).toEqual(mockInsightsResponse);
  });

  it("throws ApiError on failed response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ detail: "Repository not found" }),
    });

    await expect(getRepository(99)).rejects.toThrow("Repository not found");
  });
});
