import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ProgressBar from "./ProgressBar";

describe("ProgressBar", () => {
  it("has a segment per card, lit up to the current one, and says where you are", () => {
    render(<ProgressBar count={6} at={2} />);
    const bar = screen.getByRole("img", { name: "Question 3 of 6" });
    const segs = bar.querySelectorAll("[data-seg]");
    expect(segs).toHaveLength(6);
    expect([...segs].map((s) => s.hasAttribute("data-on"))).toEqual([true, true, true, false, false, false]);
  });
});
