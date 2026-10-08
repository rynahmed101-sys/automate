import { describe, expect, it } from "vitest";
import { WorkerJobCreate } from "../src/endpoints/worker/jobCreate";

describe("main worker job-create envelope parity", () => {
  it("accepts learning and research envelopes through the route's validated union", () => {
    const route = new WorkerJobCreate();
    const schema = route.schema.request.body.content["application/json"].schema;

    const learning = {
      schema_version: "automate.learning_handoff.v1",
      authority: "UNTRUSTED_LEARNING_EVIDENCE",
      request_id: "learn_test123",
      correlation_id: "corr_test123",
      source_revision: "a".repeat(40),
      artifact_type: "research_proposal",
      artifact: { id: "proposal_test" },
      provenance: {
        source_repo: "rynahmed101-sys/the-mirror",
        source_component: "research",
      },
    };

    const research = {
      schema_version: "mirror.research_job.v1",
      request_id: "research_test123",
      execution_kind: "external_research",
      target: { mirror_endpoint: "https://mirror.example/research" },
      query: "series expansions",
      providers: ["arxiv"],
      limits: {
        max_results_per_provider: 1,
        deadline_ms: 1000,
        max_response_bytes: 65536,
      },
      research_intent: {
        objective: "bounded research",
        summary: "",
        requirements: ["return observations"],
        instructions: ["do not certify"],
      },
      provenance: {
        capability_id: "stage1b.series_expansions",
        experiment_id: null,
        correlation_id: "corr_test123",
      },
    };

    expect(schema.safeParse(learning).success).toBe(true);
    expect(schema.safeParse(research).success).toBe(true);
  });
});
