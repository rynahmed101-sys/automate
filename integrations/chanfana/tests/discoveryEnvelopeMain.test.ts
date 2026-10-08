import { describe, expect, it } from "vitest";
import { DiscoveryJobEnvelope } from "../src/worker/discoveryEnvelope";

describe("main durable discovery contract", () => {
  it("accepts a one-candidate no-canonical-mutation grant", () => {
    const grant = {
      schema_version: "automate.mirror_discovery_grant.v1",
      grant_id: "dgrant_" + "a".repeat(32),
      authority: "UNTRUSTED_EXPLORATION_PERMISSION",
      issuer: "automate",
      correlation_id: "ctrl_test1234",
      issued_at: "2026-10-07T09:00:00.000Z",
      expires_at: "2026-10-07T09:15:00.000Z",
      max_candidates: 1,
      allowed_actions: ["research_world", "propose_new_capability"],
      forbidden_actions: ["mutate_canonical_inventory", "mutate_phase_ledger"],
      canonical_mutation_allowed: false,
    };
    const parsed = DiscoveryJobEnvelope.parse({
      schema_version: "mirror.discovery_job.v1",
      request_id: "djob_" + "b".repeat(32),
      action_cycle_id: "ctrl_test1234",
      execution_kind: "autonomous_discovery",
      target: { mirror_endpoint: "https://mirror.example/internal/discovery" },
      discovery_grant: grant,
      objective: "investigate one idea",
      limits: { max_tool_steps: 6, deadline_ms: 30000, max_response_bytes: 100000 },
      provenance: { parent_ids: [], requested_by: "automate" },
    });
    expect(parsed.discovery_grant.max_candidates).toBe(1);
    expect(parsed.discovery_grant.canonical_mutation_allowed).toBe(false);
  });
});
