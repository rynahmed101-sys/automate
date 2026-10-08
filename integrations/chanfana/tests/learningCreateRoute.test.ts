import { describe, expect, it } from "vitest";
import { workerRouter } from "../src/endpoints/worker/router";

describe("learning persistence route", () => {
  it("registers the learning POST route", () => {
    const routes = JSON.stringify(workerRouter);
    expect(routes).toContain("/learning");
  });
});
