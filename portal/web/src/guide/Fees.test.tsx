import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import type { Needs, ReviewNeed } from "../projects";
import { NEEDS } from "./endingFixtures";
import { Fees } from "./Fees";
import { GuideTheme } from "./theme/GuideTheme";
import { WORDS } from "./words";

test("a review that may apply is never listed as one the project needs", () => {
  const base = (NEEDS as Exclude<Needs, { refused: string }>);
  const maybe: ReviewNeed = { ...base.permits[0].reviews[0], review_key: "subdivision", name: "Subdivision (Major)",
    certainty: "may_need", plain: null };
  render(<GuideTheme><Fees needs={{ ...base, permits: [{ ...base.permits[0], reviews: [...base.permits[0].reviews, maybe] }] }} /></GuideTheme>);
  const needs = screen.getByRole("region", { name: WORDS.reviews_heading });
  expect(within(needs).queryByText("Subdivision (Major)")).toBeNull();
  expect(within(screen.getByRole("region", { name: WORDS.may_apply_heading })).getByText("Subdivision (Major)")).toBeVisible();
});
