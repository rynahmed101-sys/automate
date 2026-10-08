import { contentJson, OpenAPIRoute } from "chanfana";
import { z } from "zod";
import { HandleArgs } from "../../types";
import { WorkerPacket } from "../../worker/contracts";
import { VerificationJobEnvelope } from "../../worker/verificationEnvelope";
import { DiscoveryJobEnvelope } from "../../worker/discoveryEnvelope";
import { LearningHandoffEnvelope } from "../../worker/learningEnvelope";
import { ResearchJobEnvelope } from "../../worker/researchEnvelope";
import { FrontierJobEnvelope } from "../../worker/frontierEnvelope";

export class WorkerJobCreate extends OpenAPIRoute<HandleArgs> {
  public schema = {
    tags: ["Worker"],
    summary: "Queue a bounded Automate worker packet",
    request: {
      body: contentJson(z.union([
        WorkerPacket,
        VerificationJobEnvelope,
        LearningHandoffEnvelope,
        ResearchJobEnvelope,
        FrontierJobEnvelope,
        DiscoveryJobEnvelope,
      ])),
    },
    responses: {
      "200": {
        description: "Queued or already queued",
        ...contentJson(z.object({
          success: z.boolean(),
          jobId: z.string(),
          state: z.string(),
          requestId: z.string(),
        })),
      },
      "400": {
        description: "Invalid worker packet",
      },
      "401": {
        description: "Unauthorized",
      },
      "503": {
        description: "Worker persistence unavailable",
      },
    },
  };

  public async handle(c: HandleArgs[0]) {
    const { body } = await this.getValidatedData<typeof this.schema>();
    const now = new Date().toISOString();
    const requestId = "packet" in body ? body.packet.request_id : body.request_id;
    const capabilityId = "packet" in body
      ? body.packet.capability.id
      : "execution_kind" in body && body.execution_kind === "autonomous_discovery"
      ? "mirror:discovery"
      : "artifact_type" in body
      ? "learning:" + body.artifact_type
      : body.capability_id;

    const existing = await c.env.DB
      .prepare("SELECT id, state, request_id FROM worker_jobs WHERE request_id = ?1")
      .bind(requestId)
      .first<{ id: string; state: string; request_id: string }>();

    if (existing) {
      return {
        success: true,
        jobId: existing.id,
        state: existing.state,
        requestId: existing.request_id,
      };
    }

    const id = crypto.randomUUID();
    await c.env.DB.prepare(
      "INSERT INTO worker_jobs (id, request_id, capability_id, state, packet_json, result_json, created_at, updated_at) VALUES (?1, ?2, ?3, 'queued', ?4, NULL, ?5, ?5)"
    ).bind(
      id,
      requestId,
      capabilityId,
      JSON.stringify(body),
      now,
    ).run();

    return {
      success: true,
      jobId: id,
      state: "queued",
      requestId,
    };
  }
}
