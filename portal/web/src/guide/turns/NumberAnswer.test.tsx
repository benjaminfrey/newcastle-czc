import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import * as api from "../api";
import { GuideTheme } from "../theme/GuideTheme";
import { check, shown } from "./fixtures";
import { NumberAnswer, parseNumber } from "./NumberAnswer";

vi.mock("../api", async (orig) => ({ ...(await orig<typeof import("../api")>()), checkValue: vi.fn() }));
const checkValue = vi.mocked(api.checkValue);

const SIDE = shown({ turn_id: "setback_side_1", kind: "number", ask: "How far from the side line?",
  input: { unit: "ft", min: 0, max: 50000 } });

function mount(s = SIDE) {
  const onAnswer = vi.fn();
  render(<GuideTheme><NumberAnswer shown={s} projectId="p1" busy={false} locked={false} onAnswer={onAnswer} /></GuideTheme>);
  return { onAnswer, field: screen.getByRole("textbox", { name: s.ask }) };
}
const type = (field: HTMLElement, text: string) => fireEvent.change(field, { target: { value: text } });
const settle = async () => { await act(async () => { await vi.advanceTimersByTimeAsync(400); }); };

beforeEach(() => { vi.useFakeTimers({ shouldAdvanceTime: true }); checkValue.mockReset(); });
afterEach(() => vi.useRealTimers());

test("numbers are read the way people write them", () => {
  expect(["1,800", " 25 ", "25.5", "", "twenty", "1.2.3", "-"].map(parseNumber))
    .toEqual([1800, 25, 25.5, null, "not_a_number", "not_a_number", "not_a_number"]);
});

test("not a number is an input error, not a limit", async () => {
  const { field } = mount();
  type(field, "twenty");
  await settle();
  expect(field).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByText("Please enter a number, like 25 or 1,800.")).toBeVisible();
  expect(checkValue).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
});

test.each([
  [check({ result: "fits", room: 5 }), "Within the limit · 5 ft to spare"],
  [check({ result: "fits", room: 0 }), "Within the limit, right at it"],
  [check({ result: "outside", value: 11, room: null, gap: 4, direction: "short" }), "4 ft short of the limit here"],
  [check({ result: "cannot_check", reason: "two_districts", min: null }), "The Town will look at this one"],
])("the room left follows the check (%#)", async (c, words) => {
  checkValue.mockResolvedValue(c);
  const { field } = mount();
  type(field, "20");
  await settle();
  expect(screen.getByText(words)).toBeVisible();
  expect(field).not.toHaveAttribute("aria-invalid", "true");
});

test("a stale check never replaces a newer one", async () => {
  const pending: ((c: api.Check) => void)[] = [];
  checkValue.mockImplementation(() => new Promise((r) => pending.push(r)));
  const { field } = mount();
  for (const v of ["1", "12", "120"]) { type(field, v); await settle(); }
  expect(checkValue).toHaveBeenCalledTimes(3);
  await act(async () => {
    pending[2](check({ value: 120, room: 105 }));
    pending[1](check({ value: 12, result: "outside", gap: 3, direction: "short", room: null }));
    pending[0](check({ value: 1, result: "outside", gap: 14, direction: "short", room: null }));
  });
  expect(screen.getByText("Within the limit · 105 ft to spare")).toBeVisible();
  expect(screen.queryByText(/short of the limit/)).toBeNull();
});

test("the steppers stay in range", async () => {
  const { field } = mount(shown({ ...SIDE, input: { unit: null, min: 1, max: 4 }, ask: "How many full stories?" }));
  const less = screen.getByRole("button", { name: "Less" });
  const more = screen.getByRole("button", { name: "More" });
  await userEvent.click(more);
  expect(field).toHaveValue("1");
  await userEvent.click(less);
  expect(field).toHaveValue("1");
  for (let i = 0; i < 5; i += 1) await userEvent.click(more);
  expect(field).toHaveValue("4");
});

test("the slider marks the limit once it is known", async () => {
  checkValue.mockResolvedValue(check({ min: 15, room: 5 }));
  const { field } = mount();
  expect(screen.queryByRole("slider")).toBeNull();
  type(field, "20");
  await settle();
  const slider = screen.getByRole("slider");
  expect(slider).toHaveAttribute("aria-valuemax", "30");
  expect(slider).toHaveValue("20");
  expect(screen.getByText("Limit")).toBeVisible();
});

test("Next sends the number, and I'm not sure yet sends unsure", async () => {
  checkValue.mockResolvedValue(check());
  const { field, onAnswer } = mount();
  type(field, "1,800");
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(onAnswer).toHaveBeenLastCalledWith(1800);
  await userEvent.click(screen.getByRole("button", { name: "I'm not sure yet" }));
  expect(onAnswer).toHaveBeenLastCalledWith("unsure");
});

test("a number outside the question's range is an input error", async () => {
  const { field } = mount(shown({ ...SIDE, input: { unit: null, min: 1, max: 4 } }));
  type(field, "9");
  await settle();
  expect(screen.getByText("That number is outside what this question takes.")).toBeVisible();
  expect(checkValue).not.toHaveBeenCalled();
});
