import { WorkerResult, type WorkerPacketType, type WorkerResultType } from "./contracts";

export const DEFAULT_WORKER_MODEL = "@cf/openai/gpt-oss-20b";

const workerResultSchema = {
  type: "object",
  additionalProperties: false,
  required: ["schema_version", "request_id", "status", "changes", "tests", "unresolved"],
  properties: {
    schema_version: { type: "string", enum: ["automate.worker_result.v1"] },
    request_id: { type: "string" },
    status: { type: "string", enum: ["rejected", "proposed", "submitted", "failed"] },
    branch: { type: ["string", "null"] },
    pr_number: { type: ["integer", "null"] },
    changes: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["operation", "path", "expected_sha"],
        properties: {
          operation: { type: "string", enum: ["create", "update"] },
          path: { type: "string" },
          expected_sha: { type: ["string", "null"], pattern: "^[0-9a-f]{40}$" },
          content: { type: ["string", "null"] },
          summary: { type: ["string", "null"] },
        },
      },
    },
    tests: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["command", "status"],
        properties: {
          command: { type: "string" },
          status: { type: "string", enum: ["passed", "failed", "skipped", "not_run"] },
          detail: { type: ["string", "null"] },
        },
      },
    },
    unresolved: { type: "array", items: { type: "string" } },
    claims: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["claim", "supported"],
        properties: {
          claim: { type: "string" },
          supported: { type: "boolean" },
          evidence: { type: ["string", "null"] },
        },
      },
    },
  },
} as const;

export function buildWorkerPrompt(packet: WorkerPacketType["packet"]): string {
  return [
    "You are an untrusted implementation worker for Automate.",
    "Follow the packet exactly. Do not self-certify. Do not claim tests or repository state you did not actually observe.",
    "Return ONLY one JSON object matching automate.worker_result.v1.",
    "Until repository context is provided, do not invent exact file contents. Record missing context as unresolved instead.",
    "",
    "WORKER PACKET:",
    JSON.stringify(packet),
  ].join("\n");
}

export function parseWorkerModelResponse(raw: unknown, requestId: string): WorkerResultType {
  const response = typeof raw === "object" && raw !== null && "response" in raw
    ? (raw as { response?: unknown }).response
    : raw;

  if (typeof response !== "string") {
    throw new Error("Workers AI returned no textual JSON response");
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(response);
  } catch (error) {
    throw new Error("Workers AI returned invalid JSON: " + String(error));
  }

  if (typeof parsed !== "object" || parsed === null) {
    throw new Error("Workers AI JSON response is not an object");
  }

  const validation = WorkerResult.safeParse(parsed);
  if (!validation.success) {
    throw new Error("Workers AI returned a schema-invalid worker result: " + validation.error.message);
  }
  if (validation.data.request_id !== requestId) {
    throw new Error("Workers AI returned a mismatched request_id");
  }
  return validation.data;
}

export async function runWorkerModel(
  env: Env,
  packet: WorkerPacketType["packet"],
): Promise<WorkerResultType> {
  if (!env.AI) {
    throw new Error("Workers AI binding is unavailable");
  }

  const result = await env.AI.run(env.WORKER_MODEL || DEFAULT_WORKER_MODEL, {
    messages: [
      {
        role: "system",
        content: "You are an untrusted software-development worker. Return only JSON.",
      },
      { role: "user", content: buildWorkerPrompt(packet) },
    ],
    temperature: 0,
    max_tokens: 4000,
    response_format: {
      type: "json_schema",
      json_schema: workerResultSchema,
    },
  });

  return parseWorkerModelResponse(result, packet.request_id);
}
