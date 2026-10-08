import { WorkerPacket, type WorkerResultType, type WorkerPacketType } from "./contracts";
import { runWorkerModel } from "./model";
import { validateWorkerResultAgainstPacket } from "./guard";
import { stateForWorkerResult } from "./state";
import { validateResearchJobEnvelope, type ResearchJobEnvelopeType } from "./researchEnvelope";
import { validateVerificationJobEnvelope, type VerificationJobEnvelopeType } from "./verificationEnvelope";
import { validateLearningHandoffEnvelope, type LearningHandoffEnvelopeType } from "./learningEnvelope";
import { validateMirrorMissionEnvelope, type MirrorMissionEnvelopeType } from "./mirrorMissionEnvelope";
import { validateDiscoveryJobEnvelope, type DiscoveryJobEnvelopeType } from "./discoveryEnvelope";
import { validateFrontierJobEnvelope, type FrontierJobEnvelopeType } from "./frontierEnvelope";
import { storeLearningArtifact } from "./learningLedger";
import { executeMirrorMission } from "./mirrorMission";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export type PacketExecution =
  | { kind: "special"; state: "succeeded"; result: unknown; errors: string[] }
  | { kind: "worker"; state: "succeeded" | "failed"; result: WorkerResultType; errors: string[] };

async function boundedJsonResponse(response: Response, maxBytes: number, label: string): Promise<unknown> {
  const text = await response.text();
  if (new TextEncoder().encode(text).byteLength > maxBytes) {
    throw new Error(label + " result exceeds bounded payload size");
  }
  return JSON.parse(text);
}

async function callBounded(
  endpoint: string,
  token: string,
  payload: unknown,
  deadlineMs: number,
  maxResponseBytes: number,
  label: string,
): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), deadlineMs);
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: "Bearer " + token,
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(label + " returned HTTP " + response.status);
    return await boundedJsonResponse(response, maxResponseBytes, label);
  } finally {
    clearTimeout(timer);
  }
}

export async function executePacket(
  env: Env,
  packet: unknown,
): Promise<PacketExecution> {
  if (isRecord(packet) && packet.schema_version === "automate.verification_job.v1") {
    const verification: VerificationJobEnvelopeType = validateVerificationJobEnvelope(packet);
    if (!env.VERIFICATION_ENGINE_JOB_TOKEN || !env.VERIFICATION_ENGINE_ENDPOINT) {
      throw new Error("Verification engine endpoint or authentication is not configured");
    }
    if (verification.verifier_endpoint !== env.VERIFICATION_ENGINE_ENDPOINT) {
      throw new Error("verification endpoint is not allowlisted");
    }
    const payload = await callBounded(
      verification.verifier_endpoint,
      env.VERIFICATION_ENGINE_JOB_TOKEN,
      verification,
      verification.limits.deadline_ms,
      verification.limits.max_response_bytes,
      "verification engine",
    );
    return { kind: "special", state: "succeeded", result: payload, errors: [] };
  }

  if (isRecord(packet) && packet.schema_version === "automate.learning_handoff.v1") {
    const handoff: LearningHandoffEnvelopeType = validateLearningHandoffEnvelope(packet);
    const stored = await storeLearningArtifact(env, handoff);
    const payload = {
      schema_version: "automate.learning_handoff_ack.v1",
      authority: "UNTRUSTED_LEARNING_TRANSPORT_ACK",
      request_id: handoff.request_id,
      correlation_id: handoff.correlation_id,
      artifact_type: handoff.artifact_type,
      artifact_id: stored.id,
      artifact_sha256: stored.artifact_sha256,
      artifact: handoff.artifact,
      provenance: handoff.provenance,
      stored_at: new Date().toISOString(),
    };
    return { kind: "special", state: "succeeded", result: payload, errors: [] };
  }

  if (isRecord(packet) && packet.schema_version === "mirror.mission_job.v1") {
    const mission: MirrorMissionEnvelopeType = validateMirrorMissionEnvelope(packet);
    const result = await executeMirrorMission(env, mission);
    return { kind: "special", state: "succeeded", result, errors: [] };
  }

  if (isRecord(packet) && packet.schema_version === "mirror.research_job.v1") {
    const research: ResearchJobEnvelopeType = validateResearchJobEnvelope(packet);
    if (!env.MIRROR_RESEARCH_ENDPOINT || !env.MIRROR_RESEARCH_JOB_TOKEN) {
      throw new Error("Mirror research endpoint or authentication is not configured");
    }
    if (research.target.mirror_endpoint !== env.MIRROR_RESEARCH_ENDPOINT) {
      throw new Error("Mirror research endpoint is not allowlisted");
    }
    const payload = await callBounded(
      research.target.mirror_endpoint,
      env.MIRROR_RESEARCH_JOB_TOKEN,
      {
        query: research.query,
        providers: research.providers,
        limit: research.limits.max_results_per_provider,
        maxResponseBytes: research.limits.max_response_bytes,
        researchIntent: research.research_intent,
        correlationId: research.provenance.correlation_id,
      },
      research.limits.deadline_ms,
      research.limits.max_response_bytes,
      "Mirror research endpoint",
    );
    return { kind: "special", state: "succeeded", result: payload, errors: [] };
  }

  if (isRecord(packet) && packet.schema_version === "mirror.frontier_job.v1") {
    const frontier: FrontierJobEnvelopeType = validateFrontierJobEnvelope(packet);
    if (!env.MIRROR_FRONTIER_ENDPOINT || !env.MIRROR_FRONTIER_JOB_TOKEN) {
      throw new Error("Mirror frontier endpoint or authentication is not configured");
    }
    if (frontier.target.mirror_endpoint !== env.MIRROR_FRONTIER_ENDPOINT) {
      throw new Error("Mirror frontier endpoint is not allowlisted");
    }
    const payload = await callBounded(
      frontier.target.mirror_endpoint,
      env.MIRROR_FRONTIER_JOB_TOKEN,
      frontier,
      frontier.limits.deadline_ms,
      frontier.limits.max_response_bytes,
      "Mirror frontier endpoint",
    );
    return { kind: "special", state: "succeeded", result: payload, errors: [] };
  }

  if (isRecord(packet) && packet.schema_version === "mirror.discovery_job.v1") {
    const discovery: DiscoveryJobEnvelopeType = validateDiscoveryJobEnvelope(packet);
    if (!env.MIRROR_DISCOVERY_ENDPOINT || !env.MIRROR_DISCOVERY_JOB_TOKEN) {
      throw new Error("Mirror discovery endpoint or authentication is not configured");
    }
    if (discovery.target.mirror_endpoint !== env.MIRROR_DISCOVERY_ENDPOINT) {
      throw new Error("Mirror discovery endpoint is not allowlisted");
    }
    const payload = await callBounded(
      discovery.target.mirror_endpoint,
      env.MIRROR_DISCOVERY_JOB_TOKEN,
      {
        correlationId: discovery.discovery_grant.correlation_id,
        discoveryGrant: discovery.discovery_grant,
        objective: discovery.objective,
        maxToolSteps: discovery.limits.max_tool_steps,
      },
      discovery.limits.deadline_ms,
      discovery.limits.max_response_bytes,
      "Mirror discovery endpoint",
    );
    return { kind: "special", state: "succeeded", result: payload, errors: [] };
  }

  const parsedWorker = WorkerPacket.safeParse(packet);
  if (!parsedWorker.success) {
    throw new Error("Invalid Automate worker packet: " + parsedWorker.error.message);
  }
  const workerPacket: WorkerPacketType["packet"] = parsedWorker.data.packet;
  const result: WorkerResultType = await runWorkerModel(env, workerPacket);
  const errors = validateWorkerResultAgainstPacket(workerPacket, result);
  const state = errors.length ? "failed" : stateForWorkerResult(result);
  return { kind: "worker", state, result, errors };
}
