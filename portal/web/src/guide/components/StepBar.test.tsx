import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { StepBar } from "./StepBar";

test("the step bar says where you are, in words and to a screen reader", () => {
  render(<GuideTheme><StepBar step={3} of={6} label="The building" /></GuideTheme>);
  expect(screen.getByText("Step 3 of 6 · The building")).toBeInTheDocument();
  const bar = screen.getByRole("progressbar");
  expect(bar).toHaveAttribute("aria-valuenow", "3");
  expect(bar).toHaveAttribute("aria-valuemax", "6");
});
