import { describe, expect, it } from "vitest";
import { shown } from "./applicability";
import type { Expr } from "./expr";
import fixtures from "./applicability-fixtures.json";

type Case = { name: string; show_if: Expr | null; data: Record<string, unknown>; shown: boolean };

describe("shown (shared fixtures with the API)", () => {
  it.each(fixtures as Case[])("$name", (c) => {
    expect(shown(c.show_if, c.data)).toBe(c.shown);
  });
});
