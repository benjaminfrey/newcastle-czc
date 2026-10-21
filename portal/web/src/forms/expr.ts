// The condition language for form definitions and screener rules — the browser's
// copy of portal_api/forms/expr.py. Both are checked against expr-fixtures.json.
// A missing or null value makes a comparison unknown (null), never false.
// An "I don't know yet" answer ({unknown: true}) reads as missing.

type Path = string;
type Value = string | number | boolean;
export type Expr =
  | { all: Expr[] }
  | { any: Expr[] }
  | { not: Expr }
  | { known: Path }
  | { eq: [Path, Value] }
  | { ne: [Path, Value] }
  | { has: [Path, Value] }
  | { oneof: [Path, Value[]] }
  | { gt: [Path, number] }
  | { gte: [Path, number] }
  | { lt: [Path, number] }
  | { lte: [Path, number] };

const MISSING = Symbol("missing");

function get(data: unknown, path: Path): unknown {
  let cur: unknown = data;
  for (const part of path.split(".")) {
    if (cur === null || typeof cur !== "object" || Array.isArray(cur) || !Object.hasOwn(cur, part)) return MISSING;
    cur = (cur as Record<string, unknown>)[part];
    if (cur === null || cur === undefined) return MISSING;
  }
  return isUnknown(cur) ? MISSING : cur;
}

function isUnknown(v: unknown): boolean {
  return v !== null && typeof v === "object" && !Array.isArray(v)
    && Object.keys(v).length === 1 && (v as Record<string, unknown>).unknown === true;
}

const isScalar = (v: unknown) => v === null || ["string", "number", "boolean"].includes(typeof v);

const COMPARE = new Set(["gt", "gte", "lt", "lte"]);
const BINARY = new Set(["eq", "ne", "has", "oneof", ...COMPARE]);

// The same checks as expr.py's validate: a malformed condition throws.
export function validate(expr: unknown): void {
  if (expr === null || typeof expr !== "object" || Array.isArray(expr) || Object.keys(expr).length !== 1) {
    throw new Error("a condition is a mapping with exactly one operator");
  }
  const [op, arg] = Object.entries(expr)[0];
  if (op === "all" || op === "any") {
    if (!Array.isArray(arg)) throw new Error(`${op} takes a list of conditions`);
    arg.forEach(validate);
  } else if (op === "not") {
    validate(arg);
  } else if (op === "known") {
    if (typeof arg !== "string") throw new Error("known takes a path");
  } else if (BINARY.has(op)) {
    if (!(Array.isArray(arg) && arg.length === 2 && typeof arg[0] === "string")) throw new Error(`${op} takes [path, value]`);
    if (COMPARE.has(op) && typeof arg[1] !== "number") throw new Error(`${op} compares with a number`);
    if (op === "oneof" && !(Array.isArray(arg[1]) && arg[1].every(isScalar))) throw new Error("oneof takes [path, [values]]");
    if ((op === "eq" || op === "ne" || op === "has") && !isScalar(arg[1])) throw new Error(`${op} compares with a single value`);
  } else {
    throw new Error(`unknown operator ${op}`);
  }
}

const isNumber = (v: unknown): v is number => typeof v === "number";
const same = (a: unknown, b: unknown) => typeof a === typeof b && a === b;

export function evaluate(expr: Expr, data: Record<string, unknown>): boolean | null {
  const [op, arg] = Object.entries(expr)[0] as [string, unknown];
  if (op === "all" || op === "any") {
    const results = (arg as Expr[]).map((e) => evaluate(e, data));
    if (op === "all") return results.includes(false) ? false : results.includes(null) ? null : true;
    return results.includes(true) ? true : results.includes(null) ? null : false;
  }
  if (op === "not") {
    const r = evaluate(arg as Expr, data);
    return r === null ? null : !r;
  }
  if (op === "known") return get(data, arg as Path) !== MISSING;
  const [path, value] = arg as [Path, unknown];
  const v = get(data, path);
  if (v === MISSING) return null;
  switch (op) {
    case "eq": return same(v, value);
    case "ne": return !same(v, value);
    case "has": return Array.isArray(v) ? v.some((x) => same(x, value)) : null;
    case "oneof": return (value as unknown[]).some((x) => same(v, x));
  }
  if (!isNumber(v)) return null;
  const n = value as number;
  switch (op) {
    case "gt": return v > n;
    case "gte": return v >= n;
    case "lt": return v < n;
    case "lte": return v <= n;
  }
  throw new Error(`unknown operator ${op}`);
}
