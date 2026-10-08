import { describe, expect, it } from "vitest";
import { LearningHandoffEnvelope } from "../src/worker/learningEnvelope";

describe("learning transport contract", () => {
  it("requires the untrusted authority marker", () => {
    const result = LearningHandoffEnvelope.safeParse({
      schema_version: "automate.learning_handoff.v1",
      authority: "CERTIFIED",
      request_id: "learning_12345678",
      correlation_id: "cycle-1",
      source_revision: "a".repeat(40),
      artifact_type: "learning_experience",
      artifact: { experience_id: "exp_" + "b".repeat(32) },
      provenance: {
        source_repo: "rynahmed101-sys/automate",
        source_component: "test",
      },
    });
    expect(result.success).toBe(false);
  });

  it("accepts a bounded learning artifact", () => {
    const result = LearningHandoffEnvelope.safeParse({
      schema_version: "automate.learning_handoff.v1",
      authority: "UNTRUSTED_LEARNING_EVIDENCE",
      request_id: "learning_12345678",
      correlation_id: "cycle-1",
      source_revision: "a".repeat(40),
      artifact_type: "research_proposal",
      artifact: { proposal_id: "proposal_" + "c".repeat(32) },
      provenance: {
        source_repo: "rynahmed101-sys/the-mirror",
        source_component: "discovery",
      },
    });
    expect(result.success).toBe(true);
  });
});
