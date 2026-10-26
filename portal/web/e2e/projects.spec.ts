import { expect, test, type Page } from "@playwright/test";
import path from "node:path";
import { axe, completeProject, newEmail, sendProject, startProject } from "./helpers";

const SKETCH = path.join(import.meta.dirname, "fixtures/sketch.pdf");

// The first building's id, from its row on the buildings list.
async function firstItem(page: Page, base: string): Promise<string> {
  await page.goto(`${base}/building`);
  await page.getByRole("button", { name: /^(Finish|Change) Building 1$/ }).click();
  return new URL(page.url()).searchParams.get("item")!;
}

// Projects (projects brief, 2026-10-25): sign in first, three start cards, the dashboard with what
// the project needs, every part's cards, Check and send, Send; the window's sidebar or tab bar; no
// Code citations; dark mode.
test("a new building and a driveway, sent to the Town", async ({ page }, info) => {
  await startProject(page, [/^A new building/, /^A driveway/], newEmail(`project-${info.project.name}`));
  const base = new URL(page.url()).pathname;
  const main = page.getByRole("main");

  // The dashboard: a row per part, the parts still to add, and what it needs.
  await expect(main.getByRole("link", { name: /^New buildings/ })).toBeVisible();
  await expect(main.getByRole("link", { name: /^Driveway/ })).toBeVisible();
  await expect(main.getByRole("region", { name: "Add to your project" })).toContainText("Start or change a use");
  const building = main.getByRole("region", { name: "Building Permit" });
  await expect(building).toContainText("Structure");
  await expect(building).toContainText("Entrances");
  await expect(building.getByRole("heading", { level: 3 })).toHaveText("Building Permit · $30 when you send");

  // The window: a sidebar on a desktop, a tab bar on a phone, with the same four.
  const nav = page.getByRole("navigation", { name: "The app" });
  await expect(nav.getByRole("link")).toHaveText(["Home", "Project", "Messages", "You"]);

  await completeProject(page, SKETCH, { copyBuilding: true });
  await sendProject(page, ["Small Project Plan Application", "Driveway and Entrance Permit Application"]);
  await expect(main.locator("[data-pill]", { hasText: /^\W*Sent$/ })).toBeVisible();

  // Still editable after Send.
  await page.goto(`${base}/driveway`);
  await expect(page.getByText("The Town is reviewing this project")).toHaveCount(0);

  // No "Why we ask", no Code citations, anywhere the applicant reads.
  for (const p of [base, `${base}/your_lot`, `${base}/building`, `${base}/driveway`, `${base}/send`]) {
    await page.goto(p);
    await expect(page.locator("body")).not.toContainText(/Why we ask|Why the Code|Art\. \d/);
  }

  if (info.project.name === "phone") {
    // A building's long check page: its rows scroll, and Done stays on screen above the tab bar.
    await page.goto(`${base}/building/check?item=${await firstItem(page, base)}`);
    const done = await page.getByRole("button", { name: "Done" }).boundingBox();
    const tabs = await page.getByRole("navigation", { name: "The app" }).boundingBox();
    expect(done && tabs && done.y >= 0 && done.y + done.height <= tabs.y).toBe(true);
  }

  // Dark mode follows the device and passes the accessibility checks.
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto(base);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await axe(page, "dashboard, dark");
  await page.goto(`${base}/about_you?screen=applicant_is_owner`);
  await axe(page, "tiles, dark");
  await page.goto(`${base}/building?screen=size&item=${await firstItem(page, base)}`);
  await axe(page, "a set of values, dark");
  await page.goto(`${base}/send`);
  await axe(page, "check and send, dark");
});

test("a use project with two uses", async ({ page }, info) => {
  await startProject(page, [/^Start or change a use/], newEmail(`use-${info.project.name}`));
  const base = new URL(page.url()).pathname;
  await completeProject(page, SKETCH);
  // A second use: each chosen use gets its own review, under one Use Permit (brief §12.6).
  await page.goto(`${base}/use?screen=proposed_uses`);
  await page.getByRole("button", { name: "Add a use" }).click();
  const sheet = page.getByRole("dialog", { name: "Add a use" });
  await sheet.getByLabel("Search uses").fill("vendor market");
  await sheet.getByRole("button", { name: /^Add Farm/ }).first().click();
  await expect(sheet).toBeHidden();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.goto(base);
  const use = page.getByRole("main").getByRole("region", { name: "Use Permit" });
  await expect(use.getByRole("listitem")).toHaveCount(2);
  await expect(use.getByRole("heading", { level: 3 })).toHaveText("Use Permit · $30 when you send");
  await page.goto(`${base}/send`);
  await sendProject(page, ["Use Permit Application"]);
});
