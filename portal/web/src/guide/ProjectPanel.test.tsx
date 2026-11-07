import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { FLOOR, guide, LOT, SIDE } from "./fixtures";
import { ProjectPanel } from "./ProjectPanel";
import { GuideTheme } from "./theme/GuideTheme";
import { check, shown } from "./turns/fixtures";

const NEAREST = shown({ turn_id: "doesnt_fit:setback_side_1", ask: "That's 4 ft short.", step: SIDE.step,
  answers: [{ id: "nearest", label: "Make it 15 ft", hint: null }] });

function panel() {
  const onChange = vi.fn();
  render(<GuideTheme><ProjectPanel onChange={onChange} guide={guide({
    current: null,
    history: [{ shown: LOT, value: "yes" }, { shown: { ...FLOOR, check: check({ value: 1800, unit: "sq ft" }) }, value: 1800 },
              { shown: { ...SIDE, check: check({ result: "outside", value: 11 }) }, value: 11 }, { shown: NEAREST, value: "nearest" }],
    checks: { floor_area: check({ result: "cannot_check", value: 1800 }), setback_side_1: check({ result: "fits", value: 15 }) },
  })} /></GuideTheme>);
  return onChange;
}

test("answers are grouped by step, each with its value and a Change", async () => {
  const onChange = panel();
  expect(screen.getByText("012-034")).toBeVisible();
  const building = screen.getByRole("group", { name: "The building" });
  expect(within(building).getByText("1,800 sq ft")).toBeVisible();
  const sits = screen.getByRole("group", { name: "Where it sits" });
  expect(within(sits).getByText("15 ft")).toBeVisible();          // the nearest version, as now in force
  expect(within(sits).queryByText("Make it 15 ft")).toBeNull();   // the doesn't-fit choice is not a row
  await userEvent.click(within(sits).getByRole("button", { name: /^Change/ }));
  expect(onChange).toHaveBeenCalledWith("setback_side_1");
});

test("no limit mark is red", () => {
  panel();
  expect(screen.getByText("Fits")).toBeVisible();
  expect(screen.getByText("For the Town")).toBeVisible();
  expect(document.querySelector(".Mui-error, [class*='colorError']")).toBeNull();
});

test("the panel heads with the drawing when there is one", () => {
  render(<GuideTheme><ProjectPanel onChange={vi.fn()} guide={guide()} drawing={<p>The drawing</p>} /></GuideTheme>);
  const panel = screen.getByText("The drawing");
  expect(panel.compareDocumentPosition(screen.getByText("012-034")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});
