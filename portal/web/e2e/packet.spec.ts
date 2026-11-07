import { expect, test, type Page } from "@playwright/test";
import { axe, newEmail, startProject } from "./helpers";

// The packet (guided plan 6) on the LAN copy: a new house on lot 4-36 (D1) walked to "ready",
// then its packet read, folded and printed. One sign-in per device.

const turn = (page: Page) => page.locator("main section[data-turn]");
const question = (page: Page) => page.getByRole("main").getByRole("heading", { level: 2 }).first();

async function choose(page: Page, label: string) {
  await turn(page).getByText(label, { exact: true }).click();
}

async function number(page: Page, ask: RegExp, value: string) {
  await expect(question(page)).toHaveText(ask);
  await turn(page).getByRole("textbox").fill(value);
  await turn(page).getByRole("button", { name: "Next" }).click();
  await expect(question(page)).not.toHaveText(ask);
}

test("the packet: in order, judgment first, and on paper", async ({ page }, info) => {
  // Finding 4 of the old cards (OPEN_ITEMS): "No password" said once on the sign-in page.
  await page.goto("/");
  await expect(page.getByText(/No password/)).toHaveCount(1);

  await startProject(page, [/^A new building/], newEmail(`packet-${info.project.name}`));
  await page.getByRole("link", { name: "Try the guided version (preview)" }).click();
  await page.getByRole("list", { name: "Or choose from the list" }).getByRole("button", { name: "A new house", exact: true }).click();
  await choose(page, "Yes, that's right");
  await expect(question(page)).toHaveText("Which lot line is the front?");
  await turn(page).getByText(/^The line along /).first().click();
  await choose(page, "Yes, that's right");
  await number(page, /full stories/, "2");
  await number(page, /inside the roof/, "0");
  await choose(page, "No, or there's no basement");
  await number(page, /floor area/, "1,800");
  await number(page, /How many homes/, "1");
  await number(page, /front lot line/, "30");
  await number(page, /nearest side lot line/, "20");
  await number(page, /other side lot line/, "20");
  await number(page, /rear lot line/, "20");
  await expect(question(page)).toHaveText("Your application is ready to send");

  await page.getByRole("link", { name: "Your packet" }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+\/packet$/);
  const parts = page.getByRole("main").getByRole("heading", { level: 2 });
  await expect(parts).toHaveText(["In your own words", "Your project in the Code's terms", "Who decides",
    "The questions and your answers", "The checklist", "Your lot"]);
  await expect(page.getByText(/: The Code Enforcement Officer decides within 10 days of accepting your project\.$/)).toBeVisible();
  await axe(page, "packet");
  // For the chair's memo (plan 6, Task 6): the packet at this device's width, when asked for.
  if (process.env.PORTAL_SAMPLE_SHEET_OUT) {
    await page.screenshot({ path: `${process.env.PORTAL_SAMPLE_SHEET_OUT}/packet-${info.project.name}.png`, fullPage: true });
  }

  const fold = page.getByRole("button", { name: /^Show what fits/ });
  await expect(fold).toHaveAttribute("aria-expanded", "false");
  await fold.click();
  await expect(page.locator("[data-fits] li").first()).toBeVisible();
  await page.getByRole("button", { name: "Hide what fits" }).click();

  await page.emulateMedia({ media: "print" });
  await expect(page.locator("[data-fits] li").first()).toBeVisible();
  // The title stays on paper (and with it the draft chip, should any word be a draft again).
  await expect(page.getByRole("banner").getByText("Your packet")).toBeVisible();
  for (const b of await page.getByRole("button").all()) await expect(b).toBeHidden();
  await page.emulateMedia({ media: "screen" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
});
