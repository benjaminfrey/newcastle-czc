import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
// @ts-expect-error -- Node's types aren't installed in the web project; Vitest runs on Node.
import { readFileSync } from "node:fs";
import Icon, { ICON_NAMES } from "./Icon";

// @ts-expect-error -- Node's `process` isn't typed in the web project.
const vocabulary: string[] = readFileSync(`${process.cwd()}/../api/portal_api/forms/icons.txt`, "utf8")
  .split("\n").map((l: string) => l.trim()).filter((l: string) => l && !l.startsWith("#"));

describe("Icon", () => {
  it("draws every icon a form may name", () => {
    for (const name of vocabulary) expect(ICON_NAMES, name).toContain(name);
  });

  it("is an 18 px outline, hidden from screen readers", () => {
    const { container } = render(<Icon name="home-plus" />);
    const svg = container.querySelector("svg")!;
    expect(svg.getAttribute("width")).toBe("18");
    expect(svg.getAttribute("stroke-width")).toBe("1.75");
    expect(svg.getAttribute("aria-hidden")).toBe("true");
  });

  it("an unknown name draws nothing", () => {
    const { container } = render(<Icon name="not-an-icon" />);
    expect(container.querySelector("svg")).toBeNull();
  });
});
