import { describe, expect, it } from "vitest";
import { evaluate, type Expr } from "./expr";
import fixtures from "./expr-fixtures.json";

type Case = { name: string; expr: Expr; data: Record<string, unknown>; expect: boolean | null };

describe("evaluate (shared fixtures with the API)", () => {
  it.each(fixtures as Case[])("$name", (c) => {
    expect(evaluate(c.expr, c.data)).toBe(c.expect);
  });
});
