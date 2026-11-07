import { expect, test } from "vitest";
import { REASONS } from "./WizardPane";

test("the too-long message points to the note on Check and send, not a page that's gone", () => {
  // The chair, 2026-11-05: notes live on Check and send; there is no "Add more detail" any more.
  expect(REASONS.too_long).not.toMatch(/Add more detail/);
  expect(REASONS.too_long).toMatch(/note for the Town when you check and send/);
});
