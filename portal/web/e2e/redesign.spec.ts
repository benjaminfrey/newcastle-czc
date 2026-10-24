import { expect, test } from "@playwright/test";
import { axe, newEmail, screenerToStart } from "./helpers";

test("the wizard: one question at a time, chips and dots, no Why, the phone's Back, and dark mode", async ({ page }, info) => {
  await screenerToStart(page, "build", "Small Project Plan", newEmail(`win-${info.project.name}`));
  const base = new URL(page.url()).pathname.replace(/\/[a-z_]+$/, "");
  const pane = page.locator("[data-pane]").first();

  // A typed question has Continue; the dots count the step's questions.
  await page.goto(`${base}/about_you?screen=applicant_name`);
  await expect(page.getByRole("img", { name: /^Question 1 of \d+$/ })).toBeVisible();
  await page.getByRole("textbox", { name: "What is your full name?" }).fill("Ada Lovelace");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/screen=applicant_phone/);

  // The answer is a chip above the question; a tap goes back to it.
  await page.getByRole("button", { name: /^Ada Lovelace/ }).click();
  await expect(page).toHaveURL(/screen=applicant_name/);

  // A single choice has no Continue: a tap answers and moves on.
  await page.goto(`${base}/about_you?screen=applicant_is_owner`);
  await expect(pane.getByRole("radio", { name: "Yes", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /^(Continue|Skip for now)$/ })).toHaveCount(0);
  await pane.getByRole("radio", { name: "Yes", exact: true }).click();
  await expect(page).not.toHaveURL(/screen=applicant_is_owner/);

  // No "Why we ask", no Code citations, on the questions or on the result.
  for (const path of [`${base}/your_lot`, `${base}/the_work`, `${base}/buildings`, "/start/needs"]) {
    await page.goto(path);
    await expect(page.locator("main, body").first()).not.toContainText(/Why we ask|Why the Code|Art\. \d/);
  }

  // Site-only work has no Buildings step (the chair's ruling, 2026-10-23).
  await page.goto(`${base}/the_work`);
  for (const on of await page.locator('[role="checkbox"][aria-checked="true"]').all()) await on.click();
  await page.getByRole("checkbox", { name: /Work on the land/ }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.waitForTimeout(500);
  if (info.project.name === "desktop") {
    await expect(page.getByRole("navigation", { name: "Steps" }).locator(":scope > ul > li > a")).toHaveCount(8);
  } else {
    // Phone: Continue in the bottom bar; ‹ Back goes to the last question, Steps to the list.
    await expect(page.locator("[data-action-bar]").first()).toHaveClass(/fixed/);
    await expect(page.getByRole("button", { name: "Back" })).toBeVisible();
    await page.getByRole("link", { name: "Steps" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Your application" })).toBeVisible();
    await expect(page.getByRole("link", { name: /^Buildings/ })).toHaveCount(0);
  }

  // Dark mode follows the device and passes the accessibility checks.
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto(`${base}/about_you`);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await axe(page, "about you, dark");
  await page.goto(`${base}/about_you?screen=applicant_is_owner`);
  await axe(page, "tiles, dark");
});
