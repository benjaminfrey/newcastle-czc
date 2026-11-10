import { expect, test } from "@playwright/test";
import { axe, signInHere } from "./helpers";

// The explanation library's review page (design 2, §7) on the LAN copy: a staff account opens a
// batch, sees an entry as a resident reads it, and approves it. One sign-in, desktop only.
// The address is granted staff once on the VM (`python -m portal_api.library role … staff` in the
// api container), and the journey's decision is cleared afterwards with `mark-exported`.
export const LIBRARY_STAFF = "e2e-library-staff@example.com";

test("the review page: a batch, an entry as residents read it, and an approval", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "one sign-in: desktop only");
  await page.goto("/");
  await signInHere(page, LIBRARY_STAFF);

  await page.goto("/library");
  await expect(page.getByRole("heading", { level: 1, name: "Explanation library" })).toBeVisible();
  await page.getByRole("link", { name: "guide" }).click();
  await expect(page).toHaveURL(/\/library\/guide$/);
  const setbacks = page.getByRole("region", { name: "Why · how far from the lot lines" });
  await expect(setbacks.getByText("Each district sets how far a building sits from the lot lines.")).toBeVisible();
  await expect(setbacks.getByRole("heading", { name: "What the Code says" })).toBeVisible();
  await axe(page, "library-batch");

  await setbacks.getByRole("button", { name: "Approve" }).click();
  await expect(setbacks.getByText("Pending: approved, not yet recorded")).toBeVisible();
});
