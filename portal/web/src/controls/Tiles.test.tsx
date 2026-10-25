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

// ---- The task-list brief (§4.5): icons, the chosen edge, tiles inside a set ----

const field = (icons: boolean): FormField => ({
  id: "work", official_label: "Work", source: "question", from: null, may_correct: false, label: "What kind of work?",
  help: null, why: null, type: "choice", unit: null, min: null, max: null, required: true, allow_unknown: false,
  show_if: null, step: null, screen: null, ask_first: 0, control: "tiles", step_size: null, default: null, autocomplete: null,
  options: [{ value: "new", label: "A new building", official: "New", icon: icons ? "building-cottage" : null },
            { value: "add", label: "An addition", official: "Addition", icon: icons ? "home-plus" : null }],
});

describe("tiles", () => {
  it("an option's icon is drawn before its words", () => {
    render(<ChoiceTiles field={field(true)} value={null} onPick={vi.fn()} />);
    const tile = screen.getByRole("radio", { name: "A new building" });
    expect(tile.firstElementChild!.tagName.toLowerCase()).toBe("svg");
  });

  it("no icons, no svg", () => {
    render(<ChoiceTiles field={field(false)} value={null} onPick={vi.fn()} />);
    expect(screen.getByRole("radio", { name: "A new building" }).querySelector("svg")).toBeNull();
  });

  it("the chosen tile is marked", () => {
    render(<ChoiceTiles field={field(true)} value="add" onPick={vi.fn()} />);
    expect(screen.getByRole("radio", { name: "An addition" })).toHaveAttribute("data-chosen");
    expect(screen.getByRole("radio", { name: "A new building" })).not.toHaveAttribute("data-chosen");
  });

  it("inside a set a tap answers but doesn't move on", async () => {
    const onPick = vi.fn(); const onValue = vi.fn();
    render(<ChoiceTiles field={field(true)} value={null} onPick={onPick} onValue={onValue} tap={false} />);
    await userEvent.click(screen.getByRole("radio", { name: "An addition" }));
    expect(onValue).toHaveBeenCalledWith("add");
    expect(onPick).not.toHaveBeenCalled();
  });

  it("several choices carry icons too", () => {
    render(<MultiTiles field={{ ...field(true), type: "multichoice" }} value={["new"]} onValue={vi.fn()} />);
    const tile = screen.getByRole("checkbox", { name: "A new building" });
    expect(tile.firstElementChild!.tagName.toLowerCase()).toBe("svg");
    expect(tile).toHaveAttribute("data-chosen");
  });
});
