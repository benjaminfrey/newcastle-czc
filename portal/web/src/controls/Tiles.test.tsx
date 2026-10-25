import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { FormField } from "../applications";
import { ChoiceTiles, MultiTiles } from "./Tiles";

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
