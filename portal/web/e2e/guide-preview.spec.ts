import { expect, test } from "@playwright/test";
import { axe, newEmail, signInHere } from "./helpers";

// The guided builder's preview, on the LAN copy (built with VITE_GUIDE_PREVIEW=1).
test("the guide preview answers a question", async ({ page }, info) => {
  await page.goto("/");
  await signInHere(page, newEmail(`guide-${info.project.name}`));
  await page.goto("/guide/preview");
  await expect(page.getByRole("heading", { level: 1, name: "Your new house" })).toBeVisible();
  await axe(page, "guide preview");
  // The opening bubble is one "You said"; answering adds exactly one more, with the answer.
  const youSaid = page.getByText("You said");
  await expect(youSaid).toHaveCount(1);
  await page.getByText("No, it has full walls").click();   // the words, not the radio
  await expect(youSaid).toHaveCount(2);
  await expect(page.getByRole("main").getByText("No, it has full walls")).toHaveCount(2); // the row and the bubble
});

test("existing pages keep their look after the guide preview", async ({ page }, info) => {
  await page.goto("/");
  await signInHere(page, newEmail(`guide-look-${info.project.name}`));
  await expect(page.getByRole("link", { name: "Start a new application" })).toBeVisible();
  const look = () => page.evaluate(() => {
    const b = getComputedStyle(document.body);
    return { font: b.fontFamily, background: b.backgroundColor };
  });
  const before = await look();
  await page.goto("/guide/preview");
  await expect(page.getByRole("heading", { level: 1, name: "Your new house" })).toBeVisible();
  await page.getByRole("link", { name: "Back to Home" }).click();
  await expect(page.getByRole("link", { name: "Start a new application" })).toBeVisible();
  expect(await look()).toEqual(before);
  await expect(page.locator(".MuiScopedCssBaseline-root")).toHaveCount(0);
});
