import { describe, expect, it } from "vitest";
import { WORDS, WORD_STATUS } from "./words";

// Keep in step with NEVER_WORDS in portal/api/portal_api/guide/content.py (spec §10.3).
const NEVER = /\b(approved|denied|granted|rejected|permit issued|compliant|violates)\b/i;

function strings(x: unknown): string[] {
  if (typeof x === "string") return [x];
  if (x && typeof x === "object") return Object.values(x).flatMap(strings);
  return [];
}

describe("the guide's screen words", () => {
  it("are all draft until the chair approves them", () => expect(WORD_STATUS).toBe("draft"));

  it("never use the words that read as the Town's decision", () => {
    expect(strings(WORDS).filter((w) => NEVER.test(w))).toEqual([]);
  });

  it("are plain strings without markup", () => {
    for (const w of strings(WORDS)) expect(w).not.toMatch(/[<>]/);
  });
});
