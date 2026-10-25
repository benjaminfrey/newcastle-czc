import { expect, test } from "@playwright/test";
import path from "node:path";
import { axe, completeApplication, expectReviewComplete, newEmail, screenerToStart } from "./helpers";

const SKETCH = path.join(import.meta.dirname, "fixtures/sketch.pdf");

test("a resident applies for a Use Permit, edits on review, and adds detail", async ({ page }, info) => {
  await screenerToStart(page, "use", "Use Permit", newEmail(`use-${info.project.name}`));
  await completeApplication(page, SKETCH);
  await expectReviewComplete(page, "Use Permit Application");
  await expect(page.getByRole("link", { name: "sketch.pdf" })).toBeVisible();

  // Change opens the question's card and comes back. (The journey answered "No, I don't own it",
  // so the owner's details are already there; Yes hides them, No brings them back, kept.)
  await expect(page.getByRole("group", { name: "Property Owner (if different)" })).toBeVisible();
  await page.getByRole("link", { name: "Change Do you own this property?" }).click();
  await expect(page).toHaveURL(/screen=applicant_is_owner&return=review/);
  await page.getByRole("radio", { name: "Yes", exact: true }).click();
  await expect(page).toHaveURL(/\/review$/);
  await expect(page.getByRole("group", { name: "Property Owner (if different)" })).toHaveCount(0);
  await page.getByRole("link", { name: "Change Do you own this property?" }).click();
  await page.getByRole("radio", { name: "No", exact: true }).click();
  await expect(page).toHaveURL(/\/review$/);
  await expect(page.getByRole("group", { name: "Property Owner (if different)" })).toBeVisible();

  // Add more detail, then reload: everything is still there.
  await page.getByRole("button", { name: "Add more detail to Proposed", exact: true }).click();
  await page.getByLabel("More detail for Proposed").fill("Weekdays only, by appointment.");
  await page.getByRole("dialog", { name: "More detail" }).getByRole("button", { name: "Done" }).click();
  await expect(page.getByRole("group", { name: "Proposed", exact: true }).getByText("Weekdays only, by appointment.")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("group", { name: "Proposed", exact: true }).getByText("Weekdays only, by appointment.")).toBeVisible();
  await expect(page.getByRole("group", { name: "Applicant", exact: true }).getByText("Test Applicant")).toBeVisible();
  await axe(page, "review after reload");
});
