import { describe, expect, it } from "vitest";
import { ResearchProvider } from "../src/worker/researchEnvelope";

describe("research providers", () => {
  it("accepts physics literature providers used by Automate", () => {
    expect(ResearchProvider.parse("inspirehep")).toBe("inspirehep");
    expect(ResearchProvider.parse("semanticscholar")).toBe("semanticscholar");
  });
});
