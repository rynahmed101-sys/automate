import { OpenAPIRoute } from "chanfana";
import { contentJson } from "chanfana";
import { z } from "zod";
import { HandleArgs } from "../../types";

const Job = z.object({
  id: z.string(),
  requestId: z.string(),
  capabilityId: z.string(),
  state: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  hasResult: z.boolean(),
  resultId: z.string().nullable(),
  result: z.unknown().nullable(),
});

export class WorkerJobRead extends OpenAPIRoute<HandleArgs> {
  public schema = {
    tags: ["Worker"],
    summary: "Inspect an autonomous worker job",
    request: {
      params: z.object({ id: z.string().min(1) }),
      query: z.object({ includeResult: z.coerce.boolean().default(true) }),
    },
    responses: {
      "200": { description: "Job found", ...contentJson(z.object({ success: z.literal(true), job: Job })) },
      "401": { description: "Unauthorized" },
      "404": { description: "Job not found" },
    },
  };

  public async handle(c: HandleArgs[0]) {
    const { params, query } = await this.getValidatedData<typeof this.schema>();
    const row = await c.env.DB.prepare(
      "SELECT id, request_id, capability_id, state, created_at, updated_at, result_json FROM worker_jobs WHERE id = ?1"
    ).bind(params.id).first<{
      id: string;
      request_id: string;
      capability_id: string;
      state: string;
      created_at: string;
      updated_at: string;
      result_json: string | null;
    }>();

    if (!row) {
      return c.json({ success: false, error: "Job not found" }, 404);
    }

    let result: unknown = null;
    let resultId: string | null = null;
    if (query.includeResult && row.result_json !== null) {
      const bytes = new TextEncoder().encode(row.result_json).byteLength;
      if (bytes > 1_500_000) {
        return c.json({ success: false, error: "Persisted result exceeds bounded read size" }, 413);
      }
      try {
        result = JSON.parse(row.result_json);
      } catch {
        return c.json({ success: false, error: "Persisted result is malformed JSON" }, 500);
      }
      const digest = await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(row.result_json),
      );
      resultId = "res_" + Array.from(new Uint8Array(digest))
        .map((value) => value.toString(16).padStart(2, "0"))
        .join("");
    }

    return {
      success: true as const,
      job: {
        id: row.id,
        requestId: row.request_id,
        capabilityId: row.capability_id,
        state: row.state,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
        hasResult: row.result_json !== null,
        resultId,
        result,
      },
    };
  }
}
