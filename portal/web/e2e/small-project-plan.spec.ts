import { expect, test } from "@playwright/test";
import path from "node:path";
import { completeApplication, expectReviewComplete, newEmail, screenerToStart } from "./helpers";

const SKETCH = path.join(import.meta.dirname, "fixtures/sketch.pdf");

test("a Small Project Plan in nine steps, with a house, a detached garage and a deck", async ({ page }, info) => {
  await screenerToStart(page, "build", "Small Project Plan", newEmail(`spp-${info.project.name}`));
  if (info.project.name === "desktop") {
    const nav = page.getByRole("navigation", { name: "Steps" });
    await expect(nav.locator(":scope > ul > li > a")).toHaveCount(9);
  }
  await completeApplication(page, SKETCH, { extraBuilding: true, component: true });
  await expectReviewComplete(page, "Small Project Plan Application");
  await expect(page.getByRole("group", { name: /^Building Form — Building 2: Garage or shed/ })).toBeVisible();
  await expect(page.getByRole("group", { name: /^Components Section — Addition 1/ })).toBeVisible();
  if (info.project.name === "desktop") {
    // Steps finish with checkmarks.
    await expect(page.getByRole("navigation", { name: "Steps" }).getByRole("link", { name: /^About you, Done/ })).toBeVisible();
  }
});
