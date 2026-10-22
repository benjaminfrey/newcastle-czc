import { expect, test } from "@playwright/test";
import path from "node:path";
import { answerEverything, axe, expectReviewComplete, newEmail, screenerToStart, signInHere } from "./helpers";

const SKETCH = path.join(import.meta.dirname, "fixtures/sketch.pdf");

test("a resident applies for a Use Permit, edits on review, and adds detail", async ({ page }, info) => {
  await screenerToStart(page, "use", /Start your Use Permit application/);
  await signInHere(page, newEmail(`use-${info.project.name}`));
  await expect(page).toHaveURL(/\/applications\/[0-9a-f-]+/);
  await answerEverything(page, { adds: {}, unknownOnce: true }, SKETCH);
  await expectReviewComplete(page, "Use Permit Application");
  await expect(page.getByText(/Not known yet/).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "sketch.pdf" })).toBeVisible();

  // An edit that makes new questions apply: the owner block.
  const applicant = page.getByRole("region", { name: "Applicant", exact: true });
  await applicant.getByRole("button", { name: "Edit Applicant" }).click();
  await applicant.getByRole("radiogroup", { name: /Do you own the property/ }).getByRole("radio", { name: "No" }).check({ force: true });
  await applicant.getByRole("button", { name: "Save Applicant" }).click();
  await expect(page.getByText("A few new questions apply")).toBeVisible();
  await page.getByRole("button", { name: "Answer them" }).click();
  await answerEverything(page, { adds: {}, unknownOnce: false }, SKETCH);
  await expect(page.getByRole("region", { name: "Property Owner (if different)" })).toBeVisible();
  await expectReviewComplete(page, "Use Permit Application");

  // Add more detail, then reload: everything is still there.
  const proposed = page.getByRole("region", { name: "Proposed", exact: true });
  await proposed.getByRole("button", { name: "Add more detail to Proposed" }).click();
  await proposed.getByLabel("More detail for Proposed").fill("Weekdays only, by appointment.");
  await proposed.getByRole("button", { name: "Save detail for Proposed" }).click();
  // Saved once the text box closes and the button offers to change the detail.
  await expect(proposed.getByRole("button", { name: "Change the detail for Proposed" })).toBeVisible();
  await expect(proposed.getByText("Weekdays only, by appointment.")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("region", { name: "Proposed", exact: true }).getByText("Weekdays only, by appointment.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Applicant", exact: true }).getByText("Test Applicant")).toBeVisible();
  await axe(page, "review-after-reload");
});
