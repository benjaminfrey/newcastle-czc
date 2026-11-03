import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { LotFacts } from "./LotFacts";

test("unknowns are said and approximates are labeled", () => {
  render(<GuideTheme><LotFacts facts={{ map_lot: "012-034", districts: [],
    acres: { value: 0.5, approximate: true }, frontage_ft: { value: null, approximate: true } }} /></GuideTheme>);
  expect(screen.getByText("012-034")).toBeVisible();
  expect(screen.getByText(/0\.5 acres/)).toHaveTextContent("approximate, from the tax maps");
  expect(screen.getAllByText("The Town doesn't know this yet")).toHaveLength(2); // the district and the frontage
});
