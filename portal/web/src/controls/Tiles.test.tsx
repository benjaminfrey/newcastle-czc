import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { FormField } from "../applications";
import { ChoiceTiles, MultiTiles } from "./Tiles";

const f = (extra: Partial<FormField>): FormField => ({
  id: "x", official_label: "X", source: "question", from: null, may_correct: false, label: "A question?", help: null,
  why: null, type: "choice", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null,
  options: [{ value: "a", label: "Apple", official: "A" }, { value: "b", label: "Banana", official: "B" }], ...extra,
});

describe("ChoiceTiles", () => {
  it("a tap picks once and names the choice", async () => {
    const onPick = vi.fn();
    const { rerender } = render(<ChoiceTiles field={f({ type: "yesno", options: [] })} value={null} onPick={onPick} />);
    expect(screen.getByRole("radiogroup", { name: "A question?" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "No" }));
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick).toHaveBeenCalledWith(false);
    rerender(<ChoiceTiles field={f({ type: "yesno", options: [] })} value={false} onPick={onPick} />);
    expect(screen.getByRole("radio", { name: "No" })).toHaveAttribute("aria-checked", "true");
  });

  it("tapping the chosen tile again still moves on", async () => {
    const onPick = vi.fn();
    render(<ChoiceTiles field={f({})} value="a" onPick={onPick} />);
    await userEvent.click(screen.getByRole("radio", { name: "Apple" }));
    expect(onPick).toHaveBeenCalledWith("a");
  });

  it("arrow keys move between tiles, one tab stop", async () => {
    render(<ChoiceTiles field={f({})} value={null} onPick={vi.fn()} />);
    const [apple, banana] = screen.getAllByRole("radio");
    expect(apple).toHaveAttribute("tabindex", "0");
    expect(banana).toHaveAttribute("tabindex", "-1");
    apple.focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(banana).toHaveFocus();
  });
});

describe("MultiTiles", () => {
  it("toggles and shows a check", async () => {
    const onValue = vi.fn();
    const { rerender } = render(<MultiTiles field={f({ type: "multichoice" })} value={null} onValue={onValue} />);
    await userEvent.click(screen.getByRole("checkbox", { name: "Banana" }));
    expect(onValue).toHaveBeenCalledWith(["b"]);
    rerender(<MultiTiles field={f({ type: "multichoice" })} value={["b"]} onValue={onValue} />);
    expect(screen.getByRole("checkbox", { name: "Banana" })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("checkbox", { name: "Banana" }));
    expect(onValue).toHaveBeenLastCalledWith(null); // nothing chosen is no answer
  });
});
