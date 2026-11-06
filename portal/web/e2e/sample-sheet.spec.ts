import { expect, test } from "@playwright/test";
import { newEmail, startProject } from "./helpers";

// The pictures for the chair's sample sheet (guided plan 5, Task 6), taken from the LAN copy.
// Runs only when PORTAL_SAMPLE_SHEET_OUT names a folder; one sign-in, desktop only.
const OUT = process.env.PORTAL_SAMPLE_SHEET_OUT;

test("the sample sheet's pictures", async ({ page }, info) => {
  test.skip(!OUT || info.project.name !== "desktop", "only for the sample sheet, once");
  await page.setViewportSize({ width: 1280, height: 1000 });
  await startProject(page, [/^A new building/], newEmail("sample-sheet"));
  await page.getByRole("link", { name: "Try the guided version (preview)" }).click();
  const scene = page.getByRole("img", { name: /^A Newcastle lot/ });
  await expect(scene).toBeVisible();
  await scene.screenshot({ path: `${OUT}/scene-1280.png` });

  // Close-ups: a box around each pin and the thing it stands over.
  for (const spot of ["deck", "solar", "house_outline"]) {
    const pin = (await page.locator(`[data-spot="${spot}"] circle[data-hit]`).boundingBox())!;
    const cx = pin.x + pin.width / 2; const cy = pin.y + pin.height / 2;
    await page.screenshot({ path: `${OUT}/spot-${spot}.png`, clip: { x: cx - 160, y: cy - 60, width: 320, height: 220 } });
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(scene).toBeVisible();
  await scene.screenshot({ path: `${OUT}/scene-390.png` });

  await page.setViewportSize({ width: 1280, height: 1000 });
  await page.getByRole("list", { name: "Or choose from the list" }).getByRole("button", { name: "A new house", exact: true }).click();
  const main = page.getByRole("main");
  await main.getByText("Yes, that's right", { exact: true }).click();
  await main.getByText(/^The line along /).first().click();
  await main.getByText("Yes, that's right", { exact: true }).click();
  const card = page.locator("article").filter({ has: page.getByRole("img", { name: /^A house cut open/ }) });
  await expect(card).toBeVisible();
  await card.screenshot({ path: `${OUT}/stories-card.png` });
});
