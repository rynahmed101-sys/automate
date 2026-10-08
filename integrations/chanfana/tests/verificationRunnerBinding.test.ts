import { describe, expect, it } from "vitest";
import {
  validateVerificationResultIdentity,
} from "../src/worker/jobRunner";
import { VerificationJobEnvelope } from "../src/worker/verificationEnvelope";

const verification = VerificationJobEnvelope.parse({
  schema_version: "automate.verification_job.v1",
  request_id: "ver_" + "a".repeat(32),
  action_cycle_id: "cycle_test123",
  workflow_kind: "mirror_verification",
  capability_id: "stage1b.series_expansions",
  source_revision: "b".repeat(40),
  source_repository: "rynahmed101-sys/automate",
  source_branch: "feat/stage1b.series_expansions-" + "c".repeat(12),
  verifier_endpoint: "https://example.invalid/verification",
  limits: {
    deadline_ms: 120000,
    max_response_bytes: 65536,
  },
  payload: {},
  provenance: {
    parent_ids: ["wrk_parent123"],
    requested_by: "automate",
  },
});

describe("verification runner identity binding", () => {
  it("accepts matching request and revision", () => {
    expect(() =>
      validateVerificationResultIdentity(
        {
          request_id: verification.request_id,
          source_revision: verification.source_revision,
          evidence_state: "VERIFIED",
        },
        verification,
      )
    ).not.toThrow();
  });

  it("rejects a result bound to a different request", () => {
    expect(() =>
      validateVerificationResultIdentity(
        {
          request_id: "ver_" + "d".repeat(32),
          source_revision: verification.source_revision,
        },
        verification,
      )
    ).toThrow(/request_id/);
  });

  it("rejects a result bound to a different revision", () => {
    expect(() =>
      validateVerificationResultIdentity(
        {
          request_id: verification.request_id,
          source_revision: "e".repeat(40),
        },
        verification,
      )
    ).toThrow(/source_revision/);
  });
});
