import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { Bubble } from "./Bubble";

test("a bubble tells a screen reader who is speaking", () => {
  render(<GuideTheme><Bubble from="you">I want a 3-story house.</Bubble>
    <Bubble from="app">Good news.</Bubble></GuideTheme>);
  expect(screen.getByText("You said")).toBeInTheDocument();
  expect(screen.getByText("Newcastle")).toBeInTheDocument();
  expect(screen.getByText("I want a 3-story house.")).toBeInTheDocument();
});
