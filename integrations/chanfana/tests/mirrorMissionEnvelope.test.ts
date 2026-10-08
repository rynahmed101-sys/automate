import { describe, expect, it } from "vitest";
import { MirrorMissionEnvelope, validateMirrorMissionEnvelope } from "../src/worker/mirrorMissionEnvelope";

const sha = "a".repeat(40);

describe("Mirror mission envelope", () => {
  it("accepts an exact revision and non-deployed Actions target", () => {
    const value = validateMirrorMissionEnvelope({
      schema_version: "mirror.mission_job.v1",
      request_id: "mirror_test_123",
      execution_kind: "mirror_autonomous_mission",
      target: {
        repository: "rynahmed101-sys/the-mirror",
        workflow: "autonomous-mission.yml",
        ref: "main",
      },
      mission: { objective: "research and propose a capability" },
      source_revision: sha,
      limits: { deadline_ms: 120000, max_response_bytes: 500000 },
      provenance: {
        capability_id: "stage1b.demo",
        correlation_id: "corr_demo",
        requested_by: "automate",
      },
    });
    expect(value.target.repository).toBe("rynahmed101-sys/the-mirror");
  });

  it("rejects non-SHA source revisions", () => {
    expect(() => MirrorMissionEnvelope.parse({
      schema_version: "mirror.mission_job.v1",
      request_id: "mirror_test_123",
      execution_kind: "mirror_autonomous_mission",
      target: { repository: "rynahmed101-sys/the-mirror", workflow: "autonomous-mission.yml", ref: "main" },
      mission: { objective: "test" },
      source_revision: "main",
      limits: { deadline_ms: 120000, max_response_bytes: 500000 },
      provenance: { capability_id: "x", correlation_id: "y", requested_by: "automate" },
    })).toThrow();
  });
});
