import { z } from "zod";

/**
 * Durable Mirror autonomous-discovery execution envelope.
 * Chanfana owns delivery, retry, lease, persistence and bounded result readback.
 * Mirror owns research/exploration; Automate owns triage and canonical admission.
 */
export const DiscoveryJobEnvelope = z.object({
  schema_version: z.literal("mirror.discovery_job.v1"),
  request_id: z.string().regex(/^djob_[0-9a-f]{32}$/),
  action_cycle_id: z.string().min(8).max(128),
  execution_kind: z.literal("autonomous_discovery"),
  target: z.object({
    mirror_endpoint: z.string().url(),
  }),
  discovery_grant: z.object({
    schema_version: z.literal("automate.mirror_discovery_grant.v1"),
    grant_id: z.string().min(8).max(128),
    authority: z.literal("UNTRUSTED_EXPLORATION_PERMISSION"),
    issuer: z.literal("automate"),
    correlation_id: z.string().min(8).max(128),
    issued_at: z.string().min(1).max(64),
    expires_at: z.string().min(1).max(64),
    max_candidates: z.literal(1),
    allowed_actions: z.array(z.string().min(1).max(128)).min(1).max(10),
    forbidden_actions: z.array(z.string().min(1).max(128)).max(20),
    canonical_mutation_allowed: z.literal(false),
  }),
  objective: z.string().min(1).max(1000),
  limits: z.object({
    max_tool_steps: z.number().int().min(1).max(8),
    deadline_ms: z.number().int().min(1_000).max(300_000),
    max_response_bytes: z.number().int().min(65_536).max(1_500_000),
  }),
  provenance: z.object({
    parent_ids: z.array(z.string().min(1).max(128)).max(50),
    requested_by: z.literal("automate"),
  }),
});

export type DiscoveryJobEnvelopeType = z.infer<typeof DiscoveryJobEnvelope>;

export function validateDiscoveryJobEnvelope(input: unknown): DiscoveryJobEnvelopeType {
  const parsed = DiscoveryJobEnvelope.safeParse(input);
  if (!parsed.success) {
    throw new Error("Invalid discovery job envelope: " + parsed.error.message);
  }
  return parsed.data;
}
