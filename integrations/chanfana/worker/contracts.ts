import { z } from "zod";

export const WorkerChange = z.object({
  operation: z.enum(["create", "update"]),
  path: z.string().min(1).max(500),
  expected_sha: z.string().regex(/^[0-9a-f]{40}$/).nullable(),
  content: z.string().max(200_000).nullable().optional(),
  summary: z.string().max(1_000).nullable().optional(),
});

export const WorkerTest = z.object({
  command: z.string().max(1_000),
  status: z.enum(["passed", "failed", "skipped", "not_run"]),
  detail: z.string().max(2_000).nullable().optional(),
});

export const WorkerClaim = z.object({
  claim: z.string().max(2_000),
  supported: z.boolean(),
  evidence: z.string().max(2_000).nullable().optional(),
});

export const WorkerResult = z.object({
  schema_version: z.literal("automate.worker_result.v1"),
  request_id: z.string().min(8).max(128),
  status: z.enum(["rejected", "proposed", "submitted", "failed"]),
  branch: z.string().nullable().optional(),
  pr_number: z.number().int().positive().nullable().optional(),
  changes: z.array(WorkerChange).max(100),
  tests: z.array(WorkerTest),
  unresolved: z.array(z.string().max(2_000)),
  claims: z.array(WorkerClaim).optional(),
});

const WorkerContextFile = z.object({
  path: z.string().min(1).max(500),
  sha: z.string().regex(/^[0-9a-f]{40}$/),
  content: z.string().max(100_000),
});

const WorkerContext = z.object({
  files: z.array(WorkerContextFile).max(25),
  notes: z.array(z.string().max(4_000)).max(20),
});

export const WorkerPacket = z.object({
  schema_version: z.literal("automate.worker.v1"),
  packet: z.object({
    kind: z.literal("capability_implementation"),
    request_id: z.string().min(8).max(128),
    repository: z.object({
      full_name: z.string().min(1),
      base_branch: z.literal("main"),
      base_sha_claim: z.string().regex(/^[0-9a-f]{40}$/).nullable().optional(),
    }),
    capability: z.object({
      id: z.string().regex(/^[a-z0-9][a-z0-9_.-]*$/),
      stage: z.string().min(1),
      name: z.string().min(1),
      dependencies: z.array(z.string()),
    }),
    constraints: z.object({
      allowed_path_prefixes: z.array(z.string()),
      forbidden_paths: z.array(z.string()),
      branch_prefix: z.literal("feat/"),
      max_files: z.number().int().min(1).max(100),
      allow_delete: z.literal(false),
    }),
    instructions: z.array(z.string().min(1)).min(1),
    context: WorkerContext.optional(),
    verification: z.object({
      must_run_tests: z.literal(true),
      must_report_unresolved: z.literal(true),
      must_not_claim_certification: z.literal(true),
      test_targets: z.array(z.string().regex(/^tests\//)).min(1).max(20),
    }),
  }),
});

export type WorkerPacketType = z.infer<typeof WorkerPacket>;
export type WorkerResultType = z.infer<typeof WorkerResult>;
