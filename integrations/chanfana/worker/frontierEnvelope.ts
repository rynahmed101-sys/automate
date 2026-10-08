import { z } from "zod";

export const FrontierAction = z.enum([
  "repair",
  "implement",
  "research",
  "experiment",
  "create_capability_candidate",
]);

export const FrontierJobEnvelope = z.object({
  schema_version: z.literal("mirror.frontier_job.v1"),
  request_id: z.string().min(8).max(128),
  action_cycle_id: z.string().min(8).max(128),
  execution_kind: z.literal("mirror_frontier"),
  target: z.object({ mirror_endpoint: z.string().url() }),
  capability: z.object({
    id: z.string().min(1).max(128),
    name: z.string().min(1).max(500),
    task: z.string().max(4000),
    base_revision: z.string().min(7).max(64),
  }),
  mission: z.object({
    repair_required: z.boolean(),
    current_backlog: z.array(z.string()).max(50),
    ledger_frontier: z.array(z.string()).max(50),
    automate_requests: z.array(z.string()).max(50),
    discovery_allowed: z.boolean(),
    ledger_hash: z.string().max(128).nullable(),
    required_action: FrontierAction.nullable(),
  }),
  limits: z.object({
    max_tool_steps: z.number().int().min(1).max(32),
    deadline_ms: z.number().int().min(1_000).max(900_000),
    max_response_bytes: z.number().int().min(65_536).max(2_000_000),
  }),
  permissions: z.object({
    network: z.boolean(),
    workspace_write: z.boolean(),
    local_execution: z.boolean(),
    git_commit: z.boolean(),
    remote_git_mutation: z.literal(false),
    canonical_mutation: z.literal(false),
  }),
  provenance: z.object({
    correlation_id: z.string().min(8).max(128),
    parent_ids: z.array(z.string().min(1).max(128)).max(50),
  }),
});

export type FrontierJobEnvelopeType = z.infer<typeof FrontierJobEnvelope>;

export function validateFrontierJobEnvelope(input: unknown): FrontierJobEnvelopeType {
  const parsed = FrontierJobEnvelope.safeParse(input);
  if (!parsed.success) {
    throw new Error("Invalid Mirror frontier job envelope: " + parsed.error.message);
  }
  return parsed.data;
}
