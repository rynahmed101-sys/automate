import { describe, expect, it } from "vitest";
import { validateFrontierJobEnvelope } from "../src/worker/frontierEnvelope";

describe("frontier job envelope", () => {
  it("accepts bounded non-authoritative Mirror missions", () => {
    const result = validateFrontierJobEnvelope({
      schema_version: "mirror.frontier_job.v1",
      request_id: "frontier_12345678",
      action_cycle_id: "cycle_12345678",
      execution_kind: "mirror_frontier",
      target: { mirror_endpoint: "https://mirror.example/frontier" },
      capability: { id: "stage1b.test", name: "Test capability", task: "Implement", base_revision: "abcdef1234567" },
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
    });
    expect(result.permissions.canonical_mutation).toBe(false);
    expect(result.permissions.remote_git_mutation).toBe(false);
  });
});
