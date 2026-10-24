import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LotOutline, projectOutline } from "./LotDiagramLayout";

const square = { type: "MultiPolygon" as const, coordinates: [[[[-69.6, 44.0], [-69.5, 44.0], [-69.5, 44.1], [-69.6, 44.1], [-69.6, 44.0]]]] };

describe("LotDiagramLayout", () => {
  it("draws the lot from its outline", () => {
    const pts = projectOutline(square, 200, 200);
    expect(pts.length).toBe(5);
    for (const [x, y] of pts) {
      expect(x).toBeGreaterThanOrEqual(0); expect(x).toBeLessThanOrEqual(200);
      expect(y).toBeGreaterThanOrEqual(0); expect(y).toBeLessThanOrEqual(200);
    }
  });

  it("falls back to a square and says not to scale", () => {
    render(<LotOutline geometry={null} />);
    expect(screen.getByRole("img", { name: "Drawing of your lot with the building, not to scale" })).toBeInTheDocument();
    expect(screen.getByText("Not to scale")).toBeInTheDocument();
  });
});
