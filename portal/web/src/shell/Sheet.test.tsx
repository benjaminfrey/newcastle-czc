import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Sheet from "./Sheet";
import * as layout from "./useWideLayout";

describe("Sheet", () => {
  it("Esc cancels and Done calls onDone", async () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
    const onCancel = vi.fn();
    const onDone = vi.fn();
    render(<Sheet open title="Building 1" onCancel={onCancel} onDone={onDone}><p>inside</p></Sheet>);
    expect(await screen.findByText("inside")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(onDone).toHaveBeenCalled();
    await userEvent.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalled();
  });

  it("a sheet whose answers save as they're given shows Done alone, and Esc closes it the same way", async () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
    const onDone = vi.fn();
    render(<Sheet open title="Building 1" onDone={onDone}><p>inside</p></Sheet>);
    expect(await screen.findByText("inside")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(onDone).toHaveBeenCalled();
  });

  it("dots show pages", async () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(false);
    const onPage = vi.fn();
    render(<Sheet open title="Building 1" onCancel={vi.fn()} onDone={vi.fn()}
                  pages={["Basics", "Placement", "Size"]} pageIndex={1} onPage={onPage}><p>inside</p></Sheet>);
    const dots = await screen.findByRole("tablist", { name: "Pages" });
    expect(dots.querySelectorAll("[role=tab]")).toHaveLength(3);
    expect(screen.getByRole("tab", { name: "Placement" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("2 of 3")).toBeInTheDocument();
    // Back and Next sit in the footer beside the dots, always in view.
    await userEvent.click(screen.getByRole("button", { name: "Next: Size" }));
    expect(onPage).toHaveBeenLastCalledWith(2);
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(onPage).toHaveBeenLastCalledWith(0);
    await userEvent.click(screen.getByRole("tab", { name: "Size" }));
    expect(onPage).toHaveBeenCalledWith(2);
  });
});
