import { expect, test } from "@playwright/test";
import path from "node:path";
import { answerEverything, expectReviewComplete, newEmail, screenerToStart, signInHere } from "./helpers";

const SKETCH = path.join(import.meta.dirname, "fixtures/sketch.pdf");

test("a resident applies for a Small Project Plan with two buildings and a deck", async ({ page }, info) => {
  await screenerToStart(page, "build", /Start your Small Project Plan application/);
  await signInHere(page, newEmail(`spp-${info.project.name}`));
  await answerEverything(page, { adds: { building: 1, component: 1 }, unknownOnce: true }, SKETCH);
  await expectReviewComplete(page, "Small Project Plan Application");
  await expect(page.getByRole("region", { name: /^Building Form — Building 2/ })).toBeVisible();
  await expect(page.getByRole("region", { name: /^Components Section — Addition 1: deck/ })).toBeVisible();
  // The deck has no roof questions; the second floor height shows for two stories.
  const deck = page.getByRole("region", { name: /^Components Section/ });
  await expect(deck.getByText("Roof Style on Component")).toHaveCount(0);
  await expect(page.getByRole("region", { name: /^Main Building Mass Details — Building 1/ }).getByText("Second floor height")).toBeVisible();
});
