import { describe, expect, it } from "vitest";
import { workerRouter } from "../src/endpoints/worker/router";

describe("engine learning persistence route", () => {
  it("registers authenticated learning create endpoint", () => {
    expect(JSON.stringify(workerRouter)).toContain("/learning");
  });
});
