// Which questions apply — the browser's copy of the rules in
// portal_api/forms/expr.py (shown) and answers.py, checked against
// applicability-fixtures.json on both sides.
import { evaluate, type Expr } from "./expr";

// A question is asked unless its condition is known to be false: an answer still
// missing, or a property fact nobody knows, keeps the question in.
export function shown(showIf: Expr | null | undefined, data: Record<string, unknown>): boolean {
  return !showIf || evaluate(showIf, data) !== false;
}
