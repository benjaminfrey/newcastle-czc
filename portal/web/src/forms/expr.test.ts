import { describe, expect, it } from "vitest";
import { evaluate, validate, type Expr } from "./expr";
import fixtures from "./expr-fixtures.json";

type Case = { name: string; expr: Expr; data: Record<string, unknown>; expect?: boolean | null; invalid?: boolean };

describe("evaluate (shared fixtures with the API)", () => {
  it.each(fixtures as Case[])("$name", (c) => {
    if (c.invalid) {
      expect(() => validate(c.expr)).toThrow();
      return;
    }
    validate(c.expr);
    expect(evaluate(c.expr, c.data)).toBe(c.expect);
  });
});
