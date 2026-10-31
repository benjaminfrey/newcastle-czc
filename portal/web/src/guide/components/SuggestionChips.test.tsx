import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { SuggestionChips } from "./SuggestionChips";

test("chips are buttons that report their id", async () => {
  const onChip = vi.fn();
  render(<GuideTheme><SuggestionChips onChip={onChip}
    chips={[{ id: "roofs", label: "Compare roof shapes" }, { id: "town", label: "Ask the Town Office" }]} /></GuideTheme>);
  await userEvent.click(screen.getByRole("button", { name: "Ask the Town Office" }));
  expect(onChip).toHaveBeenCalledWith("town");
});
