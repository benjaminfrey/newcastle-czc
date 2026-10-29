import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Dots from "./Dots";

describe("Dots", () => {
  it("marks the current dot and names the position", () => {
    const { container } = render(<Dots count={5} index={1} />);
    expect(screen.getByRole("img", { name: "Question 2 of 5" })).toBeInTheDocument();
    const dots = container.querySelectorAll("[data-dot]");
    expect(dots).toHaveLength(5);
    expect(dots[1]).toHaveAttribute("data-current", "true");
    expect(dots[0]).not.toHaveAttribute("data-current");
  });

  it("says 13 of 20 past twelve", () => {
    const { container } = render(<Dots count={20} index={12} />);
    expect(screen.getByText("13 of 20")).toBeInTheDocument();
    expect(container.querySelectorAll("[data-dot]")).toHaveLength(0);
  });
});
