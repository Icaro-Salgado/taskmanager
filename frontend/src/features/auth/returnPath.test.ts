import { describe, expect, it } from "vitest";

import { returnPath } from "./returnPath";

describe("returnPath", () => {
  it("returns the page the user was sent away from", () => {
    expect(returnPath({ from: "/teams/2/archived?task=7" })).toBe("/teams/2/archived?task=7");
  });

  it("falls back to the home page without a usable path", () => {
    expect(returnPath(null)).toBe("/");
    expect(returnPath({})).toBe("/");
    expect(returnPath({ from: 3 })).toBe("/");
  });

  it("never leaves the app", () => {
    expect(returnPath({ from: "https://example.com/" })).toBe("/");
    expect(returnPath({ from: "//example.com/" })).toBe("/");
  });
});
