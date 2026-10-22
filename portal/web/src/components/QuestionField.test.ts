import { describe, expect, it } from "vitest";
import type { FormField } from "../applications";
import { fromDraft } from "./QuestionField";

const uses = { id: "discontinued_uses", type: "uses" } as FormField;

describe("fromDraft", () => {
  it("saves nothing for a uses question left blank", () => {
    expect(fromDraft(uses, [])).toEqual({ value: null });
    expect(fromDraft(uses, ["residence"])).toEqual({ value: ["residence"] });
  });
});
