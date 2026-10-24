import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import InsetGroup from "./InsetGroup";
import * as layout from "./useWideLayout";

describe("InsetGroup", () => {
  it("rows are at least 44px and labelled", () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
    render(
      <InsetGroup title="You" footer="We use this to reach you.">
        <InsetGroup.Row label="Phone" htmlFor="p"><input id="p" /></InsetGroup.Row>
      </InsetGroup>,
    );
    const row = screen.getByLabelText("Phone").closest("[data-row]");
    expect(row).toHaveClass("min-h-11");
    expect(screen.getByRole("group", { name: "You" })).toBeInTheDocument();
    expect(screen.getByText("We use this to reach you.")).toBeInTheDocument();
  });
});
