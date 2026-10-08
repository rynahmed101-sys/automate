import { OpenAPIRoute } from "chanfana";
import { z } from "zod";
import { HandleArgs } from "../../types";

export class WorkerHealth extends OpenAPIRoute<HandleArgs> {
  public schema = {
    tags: ["Worker"],
    summary: "Check autonomous worker availability",
    responses: {
      "200": {
        description: "Worker is available",
        content: {
          "application/json": {
            schema: z.object({
              success: z.boolean(),
              protocol: z.literal("automate.worker.v1"),
              execution: z.literal("contract_only"),
            }),
          },
        },
      },
    },
  };

  public async handle() {
    return {
      success: true,
      protocol: "automate.worker.v1" as const,
      execution: "contract_only" as const,
    };
  }
}
