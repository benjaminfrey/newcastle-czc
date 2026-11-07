import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import { guide, SIDE } from "../fixtures";
import { GuideTheme } from "../theme/GuideTheme";
import { check } from "../turns/fixtures";
import { distancesOf, DrawingList } from "./DrawingList";
import { CORNER, RECT, SECONDARY } from "./fixtures";

const rows = () => within(screen.getByRole("group", { name: "The setbacks on your lot" })).getAllByRole("listitem");

test("rows follow the roles with the API's limits", () => {
  render(<GuideTheme><DrawingList drawing={RECT} guide={guide({
    history: [{ shown: SIDE, value: 20 }], checks: { setback_side_1: check({ result: "fits", value: 20 }) },
  })} /></GuideTheme>);
  const r = rows();
  expect(r.map((x) => x.textContent)).toEqual([
    expect.stringMatching(/^FrontAt least 25 ftNot entered yet$/),
    expect.stringMatching(/^Nearest sideAt least 15 ftYours: 20 ftFits$/),
    expect.stringMatching(/^Other sideAt least 15 ftNot entered yet$/),
    expect.stringMatching(/^RearAt least 15 ftNot entered yet$/),
    expect.stringMatching(/aren't in the Town's map data/),
  ]);
});

test("a row's mark comes from guide.checks, never from comparing numbers", () => {
  // 5 ft is below the 15 ft minimum, but the API said it fits: the list shows what the API says.
  render(<GuideTheme><DrawingList drawing={RECT} guide={guide({
    history: [{ shown: SIDE, value: 5 }], checks: { setback_side_1: check({ result: "fits", value: 5 }) },
  })} /></GuideTheme>);
  expect(rows()[1]).toHaveTextContent("Fits");
  expect(rows()[1]).not.toHaveTextContent("For the Town");
});

test("a value the API replaced (Make it 15 ft) shows the API's value", () => {
  render(<GuideTheme><DrawingList drawing={RECT} guide={guide({
    history: [{ shown: SIDE, value: 11 }], checks: { setback_side_1: check({ result: "fits", value: 15 }) },
  })} /></GuideTheme>);
  expect(rows()[1]).toHaveTextContent("Yours: 15 ft");
});

test("a limit with no numbers says why", () => {
  const drawing = { ...RECT, limits: { ...RECT.limits, side: { min: null, max: null, unit: "ft", reason: "two_districts", standard_keys: [] } } };
  render(<GuideTheme><DrawingList drawing={drawing} guide={guide()} /></GuideTheme>);
  expect(rows()[1]).toHaveTextContent("Your lot is in two districts with different limits");
});

test("a frontage row says the Town decides", () => {
  render(<GuideTheme><DrawingList drawing={CORNER} guide={guide()} /></GuideTheme>);
  expect(screen.getByText("Along River Road")).toBeVisible();
  expect(screen.getByText("Along another frontage, the Town decides the setback")).toBeVisible();
});

test("before the front is chosen it says so", () => {
  render(<GuideTheme><DrawingList drawing={{ ...RECT, front: null, roles: null }} guide={guide()} /></GuideTheme>);
  expect(screen.getByText("Choose the front, and the setbacks show here.")).toBeVisible();
});

test("it says what the Town's data doesn't show", () => {
  render(<GuideTheme><DrawingList drawing={RECT} guide={guide()} /></GuideTheme>);
  expect(screen.getByText(/Water, buildings already there and easements/)).toBeVisible();
});

test("a corner lot lists its secondary front setback in place of the other side", () => {
  render(<GuideTheme><DrawingList drawing={SECONDARY} guide={guide({
    checks: { setback_secondary: check({ result: "fits", value: 25 }) },
  })} /></GuideTheme>);
  expect(rows().map((x) => x.textContent)).toEqual([
    expect.stringMatching(/^Front/),
    expect.stringMatching(/^Nearest side/),
    expect.stringMatching(/^Along River Road: the secondary front setbackAt least 20 ftYours: 25 ftFits$/),
    expect.stringMatching(/^Rear/),
    expect.stringMatching(/aren't in the Town's map data/),
  ]);
});

test("the secondary setback places the house edge beside the other road", () => {
  expect(distancesOf(guide({ checks: { setback_secondary: check({ result: "fits", value: 25 }) } }))).toEqual({ side_2: 25 });
});
