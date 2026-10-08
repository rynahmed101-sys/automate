import { contentJson, OpenAPIRoute } from "chanfana";
import { z } from "zod";
import { HandleArgs } from "../../types";
import { executePacket } from "../../worker/packetRunner";

export class WorkerJobExecute extends OpenAPIRoute<HandleArgs> {
  public schema = {
    tags: ["Worker"],
    summary: "Run one bounded AI worker attempt against a queued packet",
    request: {
      params: z.object({ id: z.string().min(1) }),
    },
    responses: {
      "200": {
        description: "Worker attempt completed",
        ...contentJson(z.object({
          success: z.boolean(),
          state: z.string(),
          result: z.unknown().nullable(),
          errors: z.array(z.string()),
        })),
      },
      "401": { description: "Unauthorized" },
      "404": { description: "Job not found" },
      "409": { description: "Job is not queued" },
      "503": { description: "AI runtime unavailable" },
    },
  };

  public async handle(c: HandleArgs[0]) {
    const { params } = await this.getValidatedData<typeof this.schema>();
    const claimed = await c.env.DB.prepare(
      "UPDATE worker_jobs SET state = 'running', updated_at = ?1 WHERE id = ?2 AND state = 'queued'"
    ).bind(new Date().toISOString(), params.id).run();

    if (!claimed.success || (claimed.meta.changes ?? 0) !== 1) {
      const row = await c.env.DB.prepare("SELECT state FROM worker_jobs WHERE id = ?1")
        .bind(params.id)
        .first<{ state: string }>();

      if (!row) return c.json({ success: false, error: "Job not found" }, 404);
      return c.json({ success: false, error: "Job is not queued" }, 409);
    }

    const row = await c.env.DB.prepare("SELECT packet_json FROM worker_jobs WHERE id = ?1")
      .bind(params.id)
      .first<{ packet_json: string }>();

    if (!row) return c.json({ success: false, error: "Job vanished after claim" }, 404);

    try {
      const stored = JSON.parse(row.packet_json);
      const packet = stored.packet;
      const execution = await executePacket(c.env, packet);
      const now = new Date().toISOString();

      const updated = await c.env.DB.prepare(
        "UPDATE worker_jobs SET state = ?1, result_json = ?2, finished_at = ?3, heartbeat_at = ?3, lease_id = NULL, lease_expires_at = NULL, updated_at = ?3, last_error = ?4 WHERE id = ?5 AND state = 'running'",
      ).bind(
        execution.state,
        JSON.stringify(execution.result),
        now,
        execution.errors.length ? execution.errors.join("; ") : null,
        params.id,
      ).run();

      if (!updated.success || (updated.meta.changes ?? 0) !== 1) {
        return c.json({ success: false, error: "Worker result lost a concurrent state transition" }, 409);
      }

      return {
        success: execution.state === "succeeded",
        state: execution.state,
        result: execution.result,
        errors: execution.errors,
      };
    } catch (error) {
      const now = new Date().toISOString();
      await c.env.DB.prepare(
        "UPDATE worker_jobs SET state = 'failed', lease_id = NULL, lease_expires_at = NULL, updated_at = ?1, last_error = ?2 WHERE id = ?3 AND state = 'running'"
      ).bind(now, error instanceof Error ? error.message : String(error), params.id).run();
      const message = error instanceof Error ? error.message : String(error);
      return c.json({ success: false, error: message }, 503);
    }
  }
}
