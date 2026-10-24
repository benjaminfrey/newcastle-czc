import { expect, test } from "@playwright/test";
import { newEmail, screenerToStart } from "./helpers";

// The antivirus test file (EICAR): harmless; every scanner flags it.
const EICAR = Buffer.from("X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*");
const EXE = Buffer.concat([Buffer.from("MZ\x90\x00\x03"), Buffer.alloc(200)]);

test("uploads that must be refused, and a second tab's save", async ({ page, context }, info) => {
  await screenerToStart(page, "driveway", "Driveway and Entrance Permit", newEmail(`refuse-${info.project.name}`));
  const base = new URL(page.url()).pathname.replace(/\/[a-z_]+$/, "");

  await page.goto(`${base}/state_permit?screen=entrance_sketch`);
  const input = page.getByLabel("Take a photo or choose a file").first();
  await input.setInputFiles({ name: "eicar.pdf", mimeType: "application/pdf", buffer: EICAR });
  await expect(page.getByRole("alert")).toContainText("virus check flagged");
  await input.setInputFiles({ name: "plan.pdf", mimeType: "application/pdf", buffer: EXE });
  await expect(page.getByRole("alert")).toContainText("PDF, JPEG, PNG or HEIC");
  await expect(page.getByRole("list", { name: "Files added" })).toHaveCount(0);

  // Two tabs: the later save is refused, and the toolbar offers to load the latest.
  const other = await context.newPage();
  await other.goto(`${base}/about_you`);
  await page.goto(`${base}/about_you`);
  const otherName = other.getByRole("textbox", { name: "What is your full name?" });
  await otherName.fill("From the other tab"); await otherName.blur();
  await expect(other.getByRole("status").first()).toHaveText("Saved");
  const name = page.getByRole("textbox", { name: "What is your full name?" });
  await name.fill("From this tab"); await name.blur();
  await expect(page.getByText("Changed in another tab").first()).toBeVisible();
  await page.getByRole("button", { name: "Load the latest" }).first().click();
  await expect(page.getByRole("textbox", { name: "What is your full name?" })).toHaveValue("From the other tab");
});
