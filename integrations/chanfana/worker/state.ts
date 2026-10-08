import type { WorkerResultType } from "./contracts";

export function stateForWorkerResult(
  result: Pick<WorkerResultType, "status">,
): "succeeded" | "failed" {
  return result.status === "failed" || result.status === "rejected"
    ? "failed"
    : "succeeded";
}
