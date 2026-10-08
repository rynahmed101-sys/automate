import { contentJson, OpenAPIRoute } from "chanfana";
import { z } from "zod";
import { HandleArgs } from "../../types";
import { LearningHandoffEnvelope } from "../../worker/learningEnvelope";

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return Array.from(new Uint8Array(digest))
    .map((item) => item.toString(16).padStart(2, "0"))
    .join("");
}

export class LearningCreate extends OpenAPIRoute<HandleArgs> {
  public schema = {
    tags: ["Learning"],
    summary: "Persist an untrusted learning artifact",
    request: {
      body: contentJson(LearningHandoffEnvelope),
    },
    responses: {
      "200": {
        description: "Learning artifact persisted",
        ...contentJson(z.object({
          success: z.literal(true),
          id: z.string(),
          artifactType: z.string(),
          artifactSha256: z.string(),
          createdAt: z.string(),
        })),
      },
      "400": { description: "Invalid learning artifact" },
      "401": { description: "Unauthorized" },
      "503": { description: "Learning persistence unavailable" },
    },
  };

  public async handle(c: HandleArgs[0]) {
    const { body } = await this.getValidatedData<typeof this.schema>();
    const artifactJson = JSON.stringify(body.artifact);
    const artifactSha256 = await sha256(artifactJson);
    const id = "learn_" + await sha256(
      body.request_id + "|" + body.artifact_type + "|" + artifactSha256,
    );
    const now = new Date().toISOString();

    try {
      await c.env.DB.prepare(
        "INSERT INTO learning_artifacts (id, artifact_type, authority, source_repo, source_revision, correlation_id, artifact_sha256, artifact_json, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?9) ON CONFLICT(id) DO UPDATE SET updated_at = ?9",
      ).bind(
        id,
        body.artifact_type,
        body.authority,
        body.provenance.source_repo,
        body.source_revision,
        body.correlation_id,
        artifactSha256,
        artifactJson,
        now,
      ).run();
    } catch (error) {
      throw new Error("learning artifact persistence failed: " + String(error));
    }

    return {
      success: true as const,
      id,
      artifactType: body.artifact_type,
      artifactSha256,
      createdAt: now,
    };
  }
}
