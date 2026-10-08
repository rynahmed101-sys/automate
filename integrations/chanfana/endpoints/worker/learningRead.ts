import { contentJson, OpenAPIRoute } from "chanfana";
import { z } from "zod";
import { HandleArgs } from "../../types";

export class LearningRead extends OpenAPIRoute<HandleArgs> {
  public schema = {
    tags: ["Learning"],
    summary: "Read durable learning artifacts without interpreting them",
    request: {
      query: z.object({
        artifactType: z.string().min(1).max(100).optional(),
        sourceRepo: z.string().min(1).max(300).optional(),
        limit: z.coerce.number().int().min(1).max(100).default(50),
      }),
    },
    responses: {
      "200": {
        description: "Learning artifacts",
        ...contentJson(z.object({
          success: z.literal(true),
          artifacts: z.array(z.object({
            id: z.string(),
            artifactType: z.string(),
            authority: z.string(),
            sourceRepo: z.string(),
            sourceRevision: z.string().nullable(),
            correlationId: z.string(),
            artifactSha256: z.string(),
            artifact: z.record(z.unknown()),
            createdAt: z.string(),
            updatedAt: z.string(),
          })),
        })),
      },
      "401": { description: "Unauthorized" },
    },
  };

  public async handle(c: HandleArgs[0]) {
    const { query } = await this.getValidatedData<typeof this.schema>();
    const conditions: string[] = [];
    const bindings: unknown[] = [];

    if (query.artifactType) {
      conditions.push("artifact_type = ?");
      bindings.push(query.artifactType);
    }
    if (query.sourceRepo) {
      conditions.push("source_repo = ?");
      bindings.push(query.sourceRepo);
    }

    const where = conditions.length ? " WHERE " + conditions.join(" AND ") : "";
    const rows = await c.env.DB.prepare(
      "SELECT id, artifact_type, authority, source_repo, source_revision, correlation_id, artifact_sha256, artifact_json, created_at, updated_at FROM learning_artifacts" +
      where +
      " ORDER BY created_at DESC, id DESC LIMIT ?",
    ).bind(...bindings, query.limit).all<{
      id: string;
      artifact_type: string;
      authority: string;
      source_repo: string;
      source_revision: string | null;
      correlation_id: string;
      artifact_sha256: string;
      artifact_json: string;
      created_at: string;
      updated_at: string;
    }>();

    return {
      success: true as const,
      artifacts: (rows.results ?? []).map((row) => ({
        id: row.id,
        artifactType: row.artifact_type,
        authority: row.authority,
        sourceRepo: row.source_repo,
        sourceRevision: row.source_revision,
        correlationId: row.correlation_id,
        artifactSha256: row.artifact_sha256,
        artifact: JSON.parse(row.artifact_json) as Record<string, unknown>,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
      })),
    };
  }
}
