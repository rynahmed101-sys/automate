import { describe, expect, it } from "vitest";
import { WorkerPacket } from "../src/worker/contracts";

describe("worker context transport", () => {
  it("preserves bounded context fields when packets are validated", () => {
    const packet = WorkerPacket.parse({
      schema_version: "automate.worker.v1",
      packet: {
        kind: "capability_implementation",
        request_id: "wrk_context_test",
        repository: {
          full_name: "rynahmed101-sys/automate",
          base_branch: "main",
          base_sha_claim: null,
        },
        capability: {
          id: "stage1b.series_expansions",
          stage: "1B",
          name: "Taylor series",
          dependencies: [],
        },
        constraints: {
          allowed_path_prefixes: ["automate/backend"],
          forbidden_paths: [],
          branch_prefix: "feat/",
          max_files: 20,
          allow_delete: false,
        },
        instructions: ["Use supplied context."],
        context: {
          files: [{ path: "docs/example.md", sha: "a".repeat(40), content: "context" }],
          notes: ["ADOPTED LESSON [les_test]: preserve assumptions"],
        },
        verification: {
          must_run_tests: true,
          must_report_unresolved: true,
          must_not_claim_certification: true,
          test_targets: ["tests/test_example.py"],
        },
        task: {
          source: "github_issue",
          ref: "141",
          summary: "Taylor series",
          requirements: ["bounded order handling"],
        },
      },
    });

    expect(packet.packet.context?.files[0].content).toBe("context");
    expect(packet.packet.context?.notes[0]).toContain("ADOPTED LESSON");
  });
});
