import { describe, expect, it } from "vitest";
import { stateForWorkerResult } from "../src/worker/state";

describe("worker result state", () => {
  it("marks failed and rejected results as failed jobs", () => {
    expect(stateForWorkerResult({ status: "failed" })).toBe("failed");
    expect(stateForWorkerResult({ status: "rejected" })).toBe("failed");
  });

  it("marks proposed and submitted results as successful jobs", () => {
    expect(stateForWorkerResult({ status: "proposed" })).toBe("succeeded");
    expect(stateForWorkerResult({ status: "submitted" })).toBe("succeeded");
  });
});
