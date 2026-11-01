import { expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import { createGuideTheme } from "./theme";
import { GuideTheme } from "./GuideTheme";
import { newcastleTokens } from "./tokens";

// createTheme keeps both schemes on the theme at run time; MUI's Theme type doesn't declare them.
const primary = (t: object, scheme: "light" | "dark") =>
  (t as { colorSchemes: Record<string, { palette: { primary: { main: string } } }> })
    .colorSchemes[scheme].palette.primary.main;

test("the theme takes its primary color from the tokens", () => {
  const t = createGuideTheme();
  expect(primary(t, "light")).toBe(newcastleTokens.color.light.primary);
  expect(primary(t, "dark")).toBe(newcastleTokens.color.dark.primary);
});

test("swapping tokens changes the look without touching components", () => {
  const warm = { ...newcastleTokens, color: { ...newcastleTokens.color,
    light: { ...newcastleTokens.color.light, primary: "#8A4B00" } } };
  expect(primary(createGuideTheme(warm), "light")).toBe("#8A4B00");
});

test("radius and spacing come from the tokens", () => {
  const t = createGuideTheme();
  expect(t.shape.borderRadius).toBe(newcastleTokens.radius.medium);
  // With CSS variables on, MUI writes spacing as calc() over its variable; the token is the fallback.
  expect(t.spacing(2)).toBe(`calc(2 * var(--mui-spacing, ${newcastleTokens.spacing}px))`);
});

test("GuideTheme scopes the baseline to its children", () => {
  render(<><p data-testid="outside">x</p><GuideTheme><p>y</p></GuideTheme></>);
  expect(document.querySelector(".MuiScopedCssBaseline-root")).not.toBeNull();
  expect(screen.getByTestId("outside").closest(".MuiScopedCssBaseline-root")).toBeNull();
});

// From the whole-branch review: targets and edges come from the tokens and meet WCAG.
type Overrides = Record<string, { styleOverrides?: Record<string, unknown> }>;
const comps = () => createGuideTheme().components as unknown as Overrides;

test("chips are at least 48 px tall", () => {
  const root = comps().MuiChip.styleOverrides!.root as { minHeight: number };
  expect(root.minHeight).toBeGreaterThanOrEqual(48);
});

test("field and chip edges use the outline token", () => {
  const { outline } = newcastleTokens.color.light;
  const css = JSON.stringify(createGuideTheme().components, (_, v) => (typeof v === "function" ? v({ theme: { vars: { palette: { outline } } } }) : v));
  expect(css).toContain(outline);
  expect(Object.keys(comps())).toEqual(expect.arrayContaining(["MuiOutlinedInput", "MuiChip"]));
});

test("headings use the display font", () => {
  const serif = { ...newcastleTokens, font: { ...newcastleTokens.font, display: "Georgia, serif" } };
  expect(createGuideTheme(serif).typography.h6.fontFamily).toBe("Georgia, serif");
  expect(createGuideTheme(serif).typography.body1.fontFamily).toBe(newcastleTokens.font.body);
});
