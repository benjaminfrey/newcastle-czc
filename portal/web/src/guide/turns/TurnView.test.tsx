import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { entry, shown } from "./fixtures";
import { TurnView } from "./TurnView";

const view = (s = shown(), more: Partial<Parameters<typeof TurnView>[0]> = {}) => {
  const onAnswer = vi.fn();
  const r = render(<GuideTheme><TurnView shown={s} projectId="p1" busy={false} locked={false} onAnswer={onAnswer} {...more} /></GuideTheme>);
  return { onAnswer, ...r };
};

test("a choice answers once, and its heading can take focus", async () => {
  const { onAnswer } = view();
  await userEvent.click(screen.getByText("Yes"));
  expect(onAnswer).toHaveBeenCalledExactlyOnceWith("yes");
  const h = screen.getByRole("heading", { level: 2, name: "How many?" });
  expect(h).toHaveAttribute("data-turn-heading");
  expect(h).toHaveAttribute("tabindex", "-1");
});

test("why and defines render as cards", () => {
  view(shown({ why: entry("setbacks", "Why · setbacks"), defines: [entry("story", "What counts as a story")] }));
  expect(screen.getAllByRole("article")).toHaveLength(2);
  expect(screen.getByText("Why · setbacks")).toBeVisible();
  expect(screen.getByText("story answer")).toBeVisible();
});

test("the doesn't-fit page is a page, not an error, with the nearest first", () => {
  const { container } = view(shown({ turn_id: "doesnt_fit:setback_side_1", ask: "That's 4 ft short of the limit here.",
    answers: [{ id: "nearest", label: "Make it 15 ft", hint: null }, { id: "keep_mine", label: "Keep my number", hint: null },
              { id: "unsure", label: "I'm not sure yet", hint: null }] }));
  expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("4 ft short");
  expect(screen.getAllByRole("radio")[0]).toHaveAccessibleName("Make it 15 ft");
  expect(container.querySelector("[aria-invalid='true'], .Mui-error")).toBeNull();
});

test("a locked turn can't be answered", async () => {
  const { onAnswer } = view(shown(), { locked: true });
  await userEvent.click(screen.getByText("Yes"));
  expect(onAnswer).not.toHaveBeenCalled();
});

test("the lot turn shows what the Town knows before its answers", () => {
  view(shown({ turn_id: "lot", kind: "lot", ask: "Is this your lot?", facts_shown: { map_lot: "012-034",
    districts: [{ code: "D1", name: "Rural" }], acres: { value: 2, approximate: true }, frontage_ft: { value: 200, approximate: true } } }));
  expect(screen.getByText("Rural")).toBeVisible();
  expect(screen.getByRole("radiogroup", { name: "Is this your lot?" })).toBeVisible();
});
