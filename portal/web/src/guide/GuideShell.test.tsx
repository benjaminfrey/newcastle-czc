import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, test } from "vitest";
import { GuideShell } from "./GuideShell";
import { GuideTheme } from "./theme/GuideTheme";

const shell = (props: Partial<Parameters<typeof GuideShell>[0]> = {}) =>
  render(<MemoryRouter><GuideTheme>
    <GuideShell title="Your new house" back={{ href: "/", label: "Home" }} {...props}>
      <p>The conversation</p>
    </GuideShell>
  </GuideTheme></MemoryRouter>);

test("the app bar names the page and offers a way back", () => {
  shell();
  expect(screen.getByRole("heading", { level: 1, name: "Your new house" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Back to Home" })).toHaveAttribute("href", "/");
  expect(screen.queryByText("Draft wording, not approved")).toBeNull();
});

test("draft wording is labelled as such", () => {
  shell({ draft: true });
  expect(screen.getByText("Draft wording, not approved")).toBeInTheDocument();
});

test("the step bar shows when there is a step", () => {
  shell({ step: { step: 3, of: 6, label: "The building" } });
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "3");
});

test("the project summary sits in an aside named Your project", () => {
  shell({ aside: <p>Summary</p> });
  expect(screen.getByRole("complementary", { name: "Your project" })).toHaveTextContent("Summary");
  expect(screen.getByRole("main")).toHaveTextContent("The conversation");
});
