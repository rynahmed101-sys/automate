import { z } from "zod";

export const MirrorMissionEnvelope = z.object({
  schema_version: z.literal("mirror.mission_job.v1"),
  request_id: z.string().min(8).max(128),
  execution_kind: z.literal("mirror_autonomous_mission"),
  target: z.object({
    repository: z.string().regex(/^[^/\s]+\/[^/\s]+$/),
    workflow: z.string().min(1).max(200),
    ref: z.string().min(1).max(200),
  }),
  mission: z.record(z.string(), z.unknown()),
  authorization: z.object({
    github_mutation_allowed: z.literal(false),
    scope: z.literal("proposal_only"),
  }),
  source_revision: z.string().regex(/^[0-9a-f]{40}$/),
  limits: z.object({
    deadline_ms: z.number().int().min(5000).max(900000),
    max_response_bytes: z.number().int().min(65536).max(1500000),
  }),
  provenance: z.object({
    capability_id: z.string().min(1).max(128),
    correlation_id: z.string().min(1).max(128),
    requested_by: z.literal("automate"),
  }),
});
export type MirrorMissionEnvelopeType = z.infer<typeof MirrorMissionEnvelope>;

export function validateMirrorMissionEnvelope(input: unknown): MirrorMissionEnvelopeType {
  const parsed = MirrorMissionEnvelope.safeParse(input);
  if (!parsed.success) throw new Error("Invalid Mirror mission envelope: " + parsed.error.message);
  if (parsed.data.mission.authorization_granted !== false) throw new Error("Mirror mission cannot carry GitHub mutation authority");
  return parsed.data;
}
