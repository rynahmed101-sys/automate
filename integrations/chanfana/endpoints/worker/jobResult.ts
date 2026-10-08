import { contentJson, OpenAPIRoute } from "chanfana";
import { z } from "zod";
import { HandleArgs } from "../../types";
import { WorkerResult } from "../../worker/contracts";
import { validateWorkerResultAgainstPacket } from "../../worker/guard";
import { stateForWorkerResult } from "../../worker/state";

export class WorkerJobResult extends OpenAPIRoute<HandleArgs> {
  public schema = {
    tags: ["Worker"],
    summary: "Submit a bounded worker result",
    request: {
      params: z.object({ id: z.string().min(1) }),
      body: contentJson(WorkerResult),
    },
    responses: {
      "200": {
        description: "Result accepted",
        ...contentJson(z.object({
          success: z.boolean(),
          state: z.string(),
          errors: z.array(z.string()),
        })),
      },
      "400": { description: "Invalid or out-of-scope result" },
      "401": { description: "Unauthorized" },
      "404": { description: "Job not found" },
      "409": { description: "Job is not running" },
    },
  };

  public async handle(c: HandleArgs[0]) {
    const { params, body } = await this.getValidatedData<typeof this.schema>();
    const row = await c.env.DB.prepare(
      "SELECT packet_json, state FROM worker_jobs WHERE id = ?1"
    ).bind(params.id).first<{ packet_json: string; state: string }>();

    if (!row) {
      return c.json({ success: false, error: "Job not found" }, 404);
    }

    let packet: z.infer<typeof import("../../worker/contracts").WorkerPacket>["packet"];
    try {
      const parsed = JSON.parse(row.packet_json);
      packet = parsed.packet;
    } catch {
      return c.json({ success: false, error: "Stored worker packet is invalid" }, 400);
    }

    if (row.state !== "running") {
      return c.json({ success: false, error: "Job must be running before a result can be submitted" }, 409);
    }

    const errors = validateWorkerResultAgainstPacket(packet, body);
    if (errors.length) {
      return {
        success: false,
        state: "failed",
        errors,
      };
    }

    const now = new Date().toISOString();
    const nextState = stateForWorkerResult(body);

    const updated = await c.env.DB.prepare(
      "UPDATE worker_jobs SET state = ?1, result_json = ?2, updated_at = ?3 WHERE id = ?4 AND state = 'running'"
    ).bind(nextState, JSON.stringify(body), now, params.id).run();

    if (!updated.success || (updated.meta.changes ?? 0) !== 1) {
      return c.json({ success: false, error: "Worker result lost a concurrent state transition" }, 409);
    }

    return {
      success: true,
      state: nextState,
      errors: [],
    };
  }
}
