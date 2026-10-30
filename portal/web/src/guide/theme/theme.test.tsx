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
