import { describe, it, expect, vi, beforeEach } from "vitest";
import { workflowApi, componentApi, integrationApi } from "@/lib/api";
import { setTokens, clearTokens } from "@/lib/auth";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
  clearTokens();
});

describe("workflowApi", () => {
  it("should list workflows with auth token", async () => {
    setTokens("test-access-token", "test-refresh-token");
    const mockData = {
      total: 2,
      runs: [
        { id: "wf-1", title: "Test 1", status: "completed", created_at: "2024-01-01", updated_at: "2024-01-01", completed_steps: 6, total_steps: 6 },
        { id: "wf-2", title: "Test 2", status: "pending", created_at: "2024-01-02", updated_at: "2024-01-02", completed_steps: 0, total_steps: 6 },
      ],
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await workflowApi.list();
    expect(result.total).toBe(2);
    expect(result.runs).toHaveLength(2);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/workflows/runs"),
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "Authorization": "Bearer test-access-token",
        }),
      }),
    );
  });

  it("should list workflows with status filter", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ total: 0, runs: [] }),
    });

    await workflowApi.list({ status: "completed" });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("status=completed"),
      expect.any(Object),
    );
  });

  it("should throw on API error", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({ detail: "Server error" }),
    });

    await expect(workflowApi.list()).rejects.toThrow("Server error");
  });

  it("should create a workflow", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        id: "wf-new",
        title: "New Workflow",
        status: "pending",
        created_at: "2024-01-01",
        updated_at: "2024-01-01",
        completed_steps: 0,
        total_steps: 6,
      }),
    });

    const result = await workflowApi.create({
      title: "New Workflow",
      requirements: "Some requirements",
    });
    expect(result.id).toBe("wf-new");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/workflows/runs"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          title: "New Workflow",
          requirements: "Some requirements",
        }),
      }),
    );
  });
});

describe("componentApi", () => {
  it("should list components", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ total: 1, components: [] }),
    });

    const result = await componentApi.list();
    expect(result.total).toBe(1);
  });

  it("should create a component", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        id: "comp-1",
        name: "Test Button",
        description: "A test button",
        category: "按钮",
        status: "active",
        tags: ["test"],
        created_at: "2024-01-01",
        updated_at: "2024-01-01",
        html_preview: "<button>Test</button>",
      }),
    });

    const result = await componentApi.create({
      name: "Test Button",
      description: "A test button",
      category: "按钮",
      html_preview: "<button>Test</button>",
    });
    expect(result.name).toBe("Test Button");
  });
});

describe("integrationApi", () => {
  it("should list integration configs", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ total: 0, configs: [] }),
    });

    const result = await integrationApi.listConfigs();
    expect(result.total).toBe(0);
  });

  it("should create an integration config", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        id: "int-1",
        name: "My Jira",
        integration_type: "jira",
        enabled: true,
        created_at: "2024-01-01",
        updated_at: "2024-01-01",
      }),
    });

    const result = await integrationApi.createConfig({
      name: "My Jira",
      integration_type: "jira",
    });
    expect(result.name).toBe("My Jira");
  });
});
