import { expect, test } from "@playwright/test";
import { axe, newEmail, screenerToStart } from "./helpers";

test("the window: site-only work, the phone's navigation, and dark mode", async ({ page }, info) => {
  await screenerToStart(page, "build", "Small Project Plan", newEmail(`win-${info.project.name}`));
  const base = new URL(page.url()).pathname.replace(/\/[a-z_]+$/, "");

  // Site-only work has no Buildings step (the chair's ruling, 2026-10-23).
  await page.goto(`${base}/the_work`);
  for (const chip of await page.getByRole("grid").getByRole("row", { selected: true }).all()) await chip.click();
  await page.getByRole("grid").getByRole("row", { name: /Work on the land/ }).click();
  await page.waitForTimeout(500);
  if (info.project.name === "desktop") {
    await expect(page.getByRole("navigation", { name: "Steps" }).locator(":scope > ul > li > a")).toHaveCount(8);
  } else {
    // Phone: Continue in the bottom bar, Back is the chevron to the list of steps.
    await expect(page.locator("[data-action-bar]").first()).toHaveClass(/fixed/);
    await expect(page.getByRole("button", { name: "Back" })).toHaveCount(0);
    await page.getByRole("link", { name: "Application" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Your application" })).toBeVisible();
    await expect(page.getByRole("link", { name: /^Buildings/ })).toHaveCount(0);
  }

  // Dark mode follows the device and passes the accessibility checks.
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto(`${base}/about_you`);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await axe(page, "about you, dark");
});
