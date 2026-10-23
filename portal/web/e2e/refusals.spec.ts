import { expect, test } from "@playwright/test";
import { newEmail, screenerToStart, signInHere } from "./helpers";

// The antivirus test file (EICAR): harmless; every scanner flags it.
const EICAR = Buffer.from("X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*");
const EXE = Buffer.concat([Buffer.from("MZ\x90\x00\x03"), Buffer.alloc(200)]);

test("uploads that must be refused, and a second tab's save", async ({ page, context }, info) => {
  await screenerToStart(page, "driveway", /Start your Driveway and Entrance Permit application/);
  await signInHere(page, newEmail(`refuse-${info.project.name}`));
  await expect(page).toHaveURL(/\/applications\/[0-9a-f-]+/);
  const appUrl = new URL(page.url()).pathname;

  await page.goto(`${appUrl}?s=entrance.entrance_sketch`);
  const input = page.locator('input[type="file"]');
  await input.setInputFiles({ name: "eicar.pdf", mimeType: "application/pdf", buffer: EICAR });
  await expect(page.getByRole("alert")).toContainText("virus check flagged");
  await input.setInputFiles({ name: "plan.pdf", mimeType: "application/pdf", buffer: EXE });
  await expect(page.getByRole("alert")).toContainText("PDF, JPEG, PNG or HEIC");
  await expect(page.getByRole("list", { name: "Files added" })).toHaveCount(0);

  // Two tabs on one application: the later save is warned about, not lost silently.
  const other = await context.newPage();
  await other.goto(`${appUrl}?s=entrance.entrance_street`);
  await page.goto(`${appUrl}?s=entrance.entrance_street`);
  await other.getByRole("textbox").first().fill("Sheepscot Road");
  await other.getByRole("button", { name: "Next" }).click();
  await expect(other.getByRole("heading", { level: 1 })).toBeVisible();
  await page.getByRole("textbox").first().fill("River Road");
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText("This application was changed in another tab or window")).toBeVisible();
  await page.getByRole("button", { name: "Load the latest" }).click();
  await expect(page.getByRole("textbox").first()).toHaveValue("Sheepscot Road");
});
