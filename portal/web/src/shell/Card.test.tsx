import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Card from "./Card";

describe("Card", () => {
  it("the header names the task and counts the cards", () => {
    render(<Card><Card.Header title="Building 1 · A home" count={6} at={2} /></Card>);
    expect(screen.getByText("Building 1 · A home")).toBeInTheDocument();
    expect(screen.getByText("3 of 6")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Question 3 of 6" })).toBeInTheDocument();
  });

  it("a header without a count has no bar", () => {
    render(<Card><Card.Header title="Buildings" aside="2 added" /></Card>);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("2 added")).toBeInTheDocument();
  });

  it("the footer has Back on the left and one filled Continue", async () => {
    const back = vi.fn(); const next = vi.fn();
    render(<Card><Card.Footer back={{ label: "Tasks", onPress: back }} next={{ label: "Continue", onPress: next }} /></Card>);
    await userEvent.click(screen.getByRole("button", { name: "Tasks" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(back).toHaveBeenCalled();
    expect(next).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Continue" })).toHaveAttribute("data-filled");
    expect(screen.getByRole("button", { name: "Tasks" })).not.toHaveAttribute("data-filled");
  });

  it("a tap card's footer shows the hint instead of Continue", () => {
    render(<Card><Card.Footer back={{ label: "Back", onPress: vi.fn() }} next={{ hint: "A tap moves on" }} /></Card>);
    expect(screen.getByText("A tap moves on")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Continue" })).not.toBeInTheDocument();
  });

  it("only the body slides, keyed by the card", () => {
    const { container } = render(
      <Card><Card.Header title="The work" count={4} at={1} /><Card.Body motionKey="a" direction={1}>Q</Card.Body></Card>);
    const body = container.querySelector("[data-card-body]")!;
    expect(body.className).toMatch(/pane-push|pane-fade/);
    expect(container.querySelector("[data-card-header]")!.className).not.toMatch(/pane-/);
  });

  it("a wide card is 760 px, else 640", () => {
    const { container, rerender } = render(<Card>x</Card>);
    expect(container.firstElementChild!.className).toContain("max-w-[640px]");
    rerender(<Card wide>x</Card>);
    expect(container.firstElementChild!.className).toContain("max-w-[760px]");
  });

  it("Return in the card means Continue", async () => {
    const submit = vi.fn();
    render(<Card onSubmit={submit}><input aria-label="Name" /></Card>);
    await userEvent.type(screen.getByRole("textbox", { name: "Name" }), "Ada{Enter}");
    expect(submit).toHaveBeenCalled();
  });
});
