import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ActionBar from "./ActionBar";

describe("ActionBar", () => {
  it("no Continue for a single choice, but the dots still show", () => {
    render(<ActionBar wide actions={{ back: vi.fn(), dots: <span>dots here</span> }} />);
    expect(screen.queryByRole("button", { name: "Continue" })).not.toBeInTheDocument();
    expect(screen.getByText("dots here")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument();
  });

  it("Skip for now on an optional, empty screen", () => {
    render(<ActionBar wide={false} actions={{ onContinue: vi.fn(), continueLabel: "Skip for now", dots: <span>d</span> }} />);
    expect(screen.getByRole("button", { name: "Skip for now" })).toBeInTheDocument();
  });
});
