import { describe, expect, it } from "vitest";

import { uniqueById } from "./uniqueById";

describe("uniqueById", () => {
  it("keeps the first item of each id, in order", () => {
    const items = [
      { id: 1, page: 1 },
      { id: 2, page: 1 },
      { id: 2, page: 2 },
      { id: 3, page: 2 },
    ];

    expect(uniqueById(items)).toEqual([
      { id: 1, page: 1 },
      { id: 2, page: 1 },
      { id: 3, page: 2 },
    ]);
  });
});
