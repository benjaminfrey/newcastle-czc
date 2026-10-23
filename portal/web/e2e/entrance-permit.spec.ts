import { expect, test } from "@playwright/test";
import path from "node:path";
import { answerEverything, expectReviewComplete, newEmail, screenerToStart, signInHere } from "./helpers";

const SKETCH = path.join(import.meta.dirname, "fixtures/sketch.pdf");

test("a resident applies for a Driveway and Entrance Permit", async ({ page }, info) => {
  await screenerToStart(page, "driveway", /Start your Driveway and Entrance Permit application/);
  await signInHere(page, newEmail(`drive-${info.project.name}`));
  await answerEverything(page, { adds: {}, unknownOnce: true }, SKETCH);
  await expectReviewComplete(page, "Entrance / Driveway Permit Application");
  await expect(page.getByText(/Marked on the map/)).toBeVisible();
});
