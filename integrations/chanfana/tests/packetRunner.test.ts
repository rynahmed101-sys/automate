import { afterEach, describe, expect, it, vi } from "vitest";
import { executePacket } from "../src/worker/packetRunner";

const frontierPacket = {
  schema_version: "mirror.frontier_job.v1",
  request_id: "frontier_12345678",
  action_cycle_id: "cycle_12345678",
  execution_kind: "mirror_frontier",
  target: { mirror_endpoint: "https://mirror.example/frontier" },
  capability: {
    id: "stage1b.test",
    name: "Test capability",
    task: "Implement",
    base_revision: "a".repeat(40),
  },
  mission: {
    repair_required: false,
    current_backlog: ["stage1b.test"],
    ledger_frontier: ["stage1b.test"],
    automate_requests: [],
    discovery_allowed: false,
    ledger_hash: null,
    required_action: "implement",
  },
  limits: { max_tool_steps: 8, deadline_ms: 300000, max_response_bytes: 1500000 },
  permissions: {
    network: true,
    workspace_write: true,
    local_execution: true,
    git_commit: true,
    remote_git_mutation: false,
    canonical_mutation: false,
  },
  provenance: { correlation_id: "corr_12345678", parent_ids: ["stage1b.test"] },
};

describe("packet execution routing", () => {
  afterEach(() => vi.restoreAllMocks());

  it("executes a Mirror frontier packet through the allowlisted endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        schema_version: "mirror.frontier_result.v1",
        authority: "UNTRUSTED_MIRROR_PROPOSAL",
        status: "NO_CHANGE_PROPOSED",
      }), { status: 200, headers: { "content-type": "application/json" } }),
    );

    const env = {
      MIRROR_FRONTIER_ENDPOINT: "https://mirror.example/frontier",
      MIRROR_FRONTIER_JOB_TOKEN: "frontier-secret",
    } as unknown as Env;

    const execution = await executePacket(env, frontierPacket);
    expect(execution.kind).toBe("special");
    expect(execution.state).toBe("succeeded");
    expect(execution.errors).toEqual([]);
    expect((execution.result as { status: string }).status).toBe("NO_CHANGE_PROPOSED");
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy.mock.calls[0][0]).toBe("https://mirror.example/frontier");
    expect(fetchSpy.mock.calls[0][1]?.headers).toMatchObject({
      authorization: "Bearer frontier-secret",
    });
  });

  it("rejects a frontier packet whose endpoint is not allowlisted", async () => {
    const env = {
      MIRROR_FRONTIER_ENDPOINT: "https://mirror.example/allowed",
      MIRROR_FRONTIER_JOB_TOKEN: "frontier-secret",
    } as unknown as Env;

    await expect(executePacket(env, frontierPacket)).rejects.toThrow("not allowlisted");
  });
});
