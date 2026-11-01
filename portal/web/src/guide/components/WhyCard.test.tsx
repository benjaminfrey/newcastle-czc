import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { WhyCard } from "./WhyCard";

const BASE = { overline: "Why · how stories are counted",
  answer: "Only floors with full-height outside walls count.",
  detail: "A finished attic doesn't count toward the limit." };

test("a why card is an article with its answer and detail", () => {
  render(<GuideTheme><WhyCard {...BASE} /></GuideTheme>);
  const card = screen.getByRole("article");
  expect(card).toHaveTextContent(BASE.answer);
  expect(card).toHaveTextContent(BASE.detail);
  expect(screen.queryByRole("link")).toBeNull();
  expect(screen.queryByRole("img")).toBeNull();
});

test("its picture is named and the Code link appears only with an address", () => {
  render(<GuideTheme><WhyCard {...BASE} picture={<svg />} pictureAlt="A house with an attic"
    codeHref="/code/9" /></GuideTheme>);
  expect(screen.getByRole("img", { name: "A house with an attic" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Read it in the Code/ })).toHaveAttribute("href", "/code/9");
});
