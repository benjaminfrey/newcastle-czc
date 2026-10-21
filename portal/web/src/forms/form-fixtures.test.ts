import { describe, expect, it } from "vitest";
import type { FormDef } from "../applications";
import { applicable, missing, printed, type Current } from "./applicability";
import fixtures from "./form-fixtures.json";

type Raw = { answers: [string, string | null, unknown][]; items: [string, string, number][];
             property: Record<string, unknown>; account: Record<string, unknown> };

function current(raw: Raw): Current {
  return { answers: raw.answers.map(([field_id, item_id, value]) => ({ field_id, item_id, value })),
           items: raw.items.map(([id, kind, position]) => ({ id, kind, position })), property: raw.property, account: raw.account };
}

// The fixture form is written for the API's loader; give the browser the fields its type expects.
const form = fixtures.form as unknown as FormDef;
for (const s of form.sections) {
  s.show_if ??= null;
  s.repeat ??= null;
  for (const f of s.fields) {
    f.may_correct ??= false; f.show_if ??= null; f.required ??= false; f.allow_unknown ??= false;
    f.options ??= []; f.from ??= null;
  }
}

describe("applicability (shared fixtures with the API)", () => {
  it.each(fixtures.cases)("$name", (c) => {
    const cur = current(c.current as unknown as Raw);
    expect(applicable(form, cur).map((r) => [r.field.id, r.itemId])).toEqual(c.applicable);
    expect(missing(form, cur)).toEqual(c.missing);
    expect(printed(form, cur).map((b) => [b.section.id, b.itemId, b.rows.map((r) => [r.field.id, r.value])])).toEqual(c.printed);
  });
});
