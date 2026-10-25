import { expect, test } from "@playwright/test";
import path from "node:path";
import { completeApplication, expectReviewComplete, newEmail, screenerToStart } from "./helpers";

const SKETCH = path.join(import.meta.dirname, "fixtures/sketch.pdf");

test("a Small Project Plan in five tasks, with a copied building and an addition", async ({ page }, info) => {
  await screenerToStart(page, "build", "Small Project Plan", newEmail(`spp-${info.project.name}`));
  if (info.project.name === "desktop") {
    // Your lot, About you, The work, Buildings, Additions; Check and send opens at the end.
    await expect(page.getByRole("navigation", { name: "Tasks" }).getByRole("link")).toHaveCount(5);
  }
  await completeApplication(page, SKETCH, { copyBuilding: true, component: true });
  await expectReviewComplete(page, "Small Project Plan Application");
  await expect(page.getByRole("group", { name: /^Building Form — Building 2/ })).toBeVisible();
  await expect(page.getByRole("group", { name: /^Components Section — Addition 1/ })).toBeVisible();
  if (info.project.name === "desktop") {
    // Tasks finish Done.
    await expect(page.getByRole("navigation", { name: "Tasks" }).getByRole("link", { name: /^About you\s*,\s*Done/ })).toBeVisible();
  }
});
