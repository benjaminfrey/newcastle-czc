import { expect, test } from "@playwright/test";
import path from "node:path";
import { axe, completeApplication, expectReviewComplete, newEmail, screenerToStart } from "./helpers";

const SKETCH = path.join(import.meta.dirname, "fixtures/sketch.pdf");

test("a resident applies for a Use Permit, edits on review, and adds detail", async ({ page }, info) => {
  await screenerToStart(page, "use", "Use Permit", newEmail(`use-${info.project.name}`));
  await completeApplication(page, SKETCH);
  await expectReviewComplete(page, "Use Permit Application");
  await expect(page.getByRole("link", { name: "sketch.pdf" })).toBeVisible();

  // Edit opens the step in a sheet; the owner's details appear in place when the switch turns off.
  await page.getByRole("button", { name: "Edit Applicant" }).click();
  const sheet = page.getByRole("dialog", { name: "About you" });
  // Click the switch's track, as a person would: its label text is for screen readers only.
  const owns = sheet.getByRole("switch", { name: "Do you own this property?" });
  await sheet.locator('[data-field="applicant_is_owner"] [data-slot="switch-control"]').click();
  await expect(owns).not.toBeChecked();
  const owner = sheet.getByRole("group", { name: "Property Owner (if different)" });
  await expect(owner).toBeVisible();
  for (const box of await owner.getByRole("textbox").all()) { await box.fill("Owner Example"); await box.blur(); }
  await sheet.getByRole("button", { name: "Done" }).click();
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
