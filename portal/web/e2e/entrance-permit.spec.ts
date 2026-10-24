import { expect, test } from "@playwright/test";
import path from "node:path";
import { completeApplication, expectReviewComplete, newEmail, screenerToStart } from "./helpers";

const SKETCH = path.join(import.meta.dirname, "fixtures/sketch.pdf");

test("a resident applies for a Driveway and Entrance Permit", async ({ page }, info) => {
  await screenerToStart(page, "driveway", "Driveway and Entrance Permit", newEmail(`drive-${info.project.name}`));
  await completeApplication(page, SKETCH);
  await expectReviewComplete(page, "Entrance / Driveway Permit Application");
  await expect(page.getByText(/Marked on the map/)).toBeVisible();
});
