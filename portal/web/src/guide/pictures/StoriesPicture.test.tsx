import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { WORDS } from "../words";
import { StoriesPicture } from "./StoriesPicture";

test("the cut-away shows the six labels and no number of its own", () => {
  const { container } = render(<GuideTheme><StoriesPicture /></GuideTheme>);
  const texts = [...container.querySelectorAll("text")].map((t) => t.textContent);
  expect([...texts].sort()).toEqual(Object.values(WORDS.pictures.stories).sort());
});

// Every picture file's source, through Vite, so no Node types are needed.
const sources = import.meta.glob(["./*.ts", "./*.tsx", "!./*.test.*"], { query: "?raw", import: "default", eager: true }) as Record<string, string>;

test("the pictures take their colours only from the theme", () => {
  expect(Object.keys(sources).length).toBeGreaterThanOrEqual(5);
  for (const [f, text] of Object.entries(sources)) expect(text, f).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
});
