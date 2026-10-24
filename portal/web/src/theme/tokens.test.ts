import { describe, expect, it } from "vitest";
import { contrast, DARK, LIGHT, type Tokens } from "./tokens";
// @ts-expect-error -- Node's types aren't installed in the web project; Vitest runs on Node.
import { readFileSync } from "node:fs";

// Read from disk: Vitest's CSS handling empties `?raw` CSS imports, and import.meta.url isn't
// always a file: URL under jsdom. Vitest runs from portal/web.
// @ts-expect-error -- Node's `process` isn't typed in the web project.
const css: string = readFileSync(`${process.cwd()}/src/index.css`, "utf8");

const MODES: [string, Tokens][] = [["light", LIGHT], ["dark", DARK]];

describe("theme tokens", () => {
  it.each(MODES)("text meets 4.5:1 on its grounds (%s)", (_, t) => {
    for (const fg of [t.label, t.secondaryLabel, t.accentText]) {
      for (const bg of [t.ground, t.row, t.groupedGround, t.fill, t.groundElevated, t.rowElevated]) {
        expect(contrast(fg, bg), `${fg} on ${bg}`).toBeGreaterThanOrEqual(4.5);
      }
    }
    expect(contrast(t.destructive, t.row)).toBeGreaterThanOrEqual(4.5);
  });

  it.each(MODES)("a field's fill stands apart from the row it sits on, in a sheet too (%s)", (_, t) => {
    expect(contrast(t.fill, t.row)).toBeGreaterThanOrEqual(1.15);
    expect(contrast(t.fill, t.rowElevated)).toBeGreaterThanOrEqual(1.15);
    expect(contrast(t.rowElevated, t.groundElevated)).toBeGreaterThanOrEqual(1.05);
  });

  it.each(MODES)("buttons meet 4.5:1 (%s)", (_, t) => {
    expect(contrast(t.onAccent, t.accent)).toBeGreaterThanOrEqual(4.5);
  });

  it("the seal colour is the seal's", () => {
    expect(LIGHT.seal).toBe("#1098A8");
    expect(DARK.seal).toBe("#1098A8");
  });

  it("contrast follows the WCAG formula", () => {
    expect(contrast("#000000", "#FFFFFF")).toBeCloseTo(21, 5);
    expect(contrast("#1098A8", "#FFFFFF")).toBeCloseTo(3.45, 1);
  });

  it("css and tokens agree", () => {
    const block = (selector: string) => css.slice(css.indexOf(selector), css.indexOf("}", css.indexOf(selector)));
    const light = block(":root {");
    const dark = block(':root[data-theme="dark"] {');
    for (const [name, value] of Object.entries(LIGHT)) {
      expect(light, `light ${name}`).toContain(`--app-${kebab(name)}: ${value};`);
    }
    for (const [name, value] of Object.entries(DARK)) {
      expect(dark, `dark ${name}`).toContain(`--app-${kebab(name)}: ${value};`);
    }
  });
});

function kebab(s: string) {
  return s.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);
}
