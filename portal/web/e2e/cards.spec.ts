import { expect, test } from "@playwright/test";
import { axe, newEmail, screenerToStart } from "./helpers";

// Tasks and cards (task-list brief, 2026-10-25): the task list with its pills, one card at a time
// with its bar, tiles with icons, a tap that moves on, no Why, the phone's footer with the keyboard
// open, and dark mode.
test("tasks and cards: the list, the bar, icons, a tap, the phone's footer, and dark mode", async ({ page }, info) => {
  await screenerToStart(page, "build", "Small Project Plan", newEmail(`cards-${info.project.name}`));
  const base = new URL(page.url()).pathname.replace(/\/[a-z_]+$/, "");
  const card = page.locator("[data-card-body]").first();

  // The task list: every task a link with its pill; Check and send closed.
  await page.goto(base);
  const main = page.getByRole("main");
  await expect(main.getByRole("link", { name: /^The work\s*,.*(Not started|\d+ of \d+ answered)$/ })).toBeVisible();
  await expect(main.getByText("Opens when the tasks above are done")).toBeVisible();

  // A card: its header names the task and counts its cards.
  await page.goto(`${base}/about_you`);
  await expect(page.getByRole("img", { name: /^Question 1 of \d+$/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Tasks" })).toBeVisible();

  // What "Do I need a permit?" asked arrives answered, says so, and its tiles carry icons.
  await page.goto(`${base}/the_work`);
  await expect(page.getByText("Filled in from your answers at the start. Change it if you need to.")).toBeVisible();
  await expect(card.getByRole("checkbox").first().locator("svg")).toBeVisible();

  // A single choice moves on at a tap, and says so the first time.
  await page.goto(`${base}/about_you?screen=applicant_is_owner`);
  await expect(card.getByRole("radio", { name: "Yes", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /^(Continue|Skip for now)$/ })).toHaveCount(0);
  await card.getByRole("radio", { name: "Yes", exact: true }).click();
  await expect(page).not.toHaveURL(/screen=applicant_is_owner/);

  // No "Why we ask", no Code citations, on the cards or the result.
  for (const path of [`${base}/your_lot`, `${base}/the_work`, `${base}/buildings`, "/start/needs"]) {
    await page.goto(path);
    await expect(page.locator("body")).not.toContainText(/Why we ask|Why the Code|Art\. \d/);
  }

  if (info.project.name === "phone") {
    // A long card on a phone: with a field focused (the keyboard up), Continue stays on screen.
    await page.goto(`${base}/about_you?screen=applicant_name`);
    await page.getByRole("textbox", { name: "Full name" }).focus();
    const box = await page.getByRole("button", { name: "Continue" }).boundingBox();
    const view = page.viewportSize()!;
    expect(box && box.y >= 0 && box.y + box.height <= view.height).toBe(true);
  }

  // Dark mode follows the device and passes the accessibility checks.
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto(base);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await axe(page, "task list, dark");
  await page.goto(`${base}/about_you?screen=applicant_is_owner`);
  await axe(page, "tiles, dark");
  await page.goto(`${base}/buildings?screen=mass_width&item=${await firstItem(page, base)}`);
  await axe(page, "a set of values, dark");
});

// The first building's id, from its link on the buildings list.
async function firstItem(page: import("@playwright/test").Page, base: string): Promise<string> {
  await page.goto(`${base}/buildings`);
  await page.getByRole("button", { name: /^(Finish|Change) Building 1$/ }).click();
  return new URL(page.url()).searchParams.get("item")!;
}
