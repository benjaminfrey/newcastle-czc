import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import AnswerTrail from "./AnswerTrail";

describe("AnswerTrail", () => {
  it("chips go back to their question", async () => {
    const onGo = vi.fn();
    render(<AnswerTrail chips={[{ id: "name", text: "Ada Lovelace", carried: false }, { id: "phone", text: "207-555-0100", carried: false }]} onGo={onGo} />);
    await userEvent.click(screen.getByRole("button", { name: /207-555-0100/ }));
    expect(onGo).toHaveBeenCalledWith("phone");
  });

  it("carried chips are dashed and say so", () => {
    render(<AnswerTrail chips={[{ id: "works", text: "A new building", carried: true }]} onGo={vi.fn()} />);
    const chip = screen.getByRole("button", { name: /A new building/ });
    expect(chip).toHaveAttribute("data-carried", "true");
    expect(chip).toHaveAccessibleName(/from your answers at the start/);
  });

  it("keeps to the last four answers, with the earlier ones a tap away", async () => {
    const chips = ["a", "b", "c", "d", "e", "f", "g"].map((x) => ({ id: x, text: `Answer ${x}`, carried: false }));
    render(<AnswerTrail chips={chips} onGo={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /Answer a/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Answer d/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Answer g/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Show 3 earlier answers" }));
    expect(screen.getByRole("button", { name: /Answer a/ })).toBeInTheDocument();
  });

  it("before the first answer it says what will appear", () => {
    render(<AnswerTrail chips={[]} onGo={vi.fn()} />);
    expect(screen.getByText("Your answers appear here as you go")).toBeInTheDocument();
  });
});
