import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { AnswerList } from "./AnswerList";

const ANSWERS = [{ id: "yes", label: "Yes, inside the roof", hint: "like a finished attic" },
                 { id: "no", label: "No, it has full walls" },
                 { id: "unsure", label: "I'm not sure yet" }];
const Q = "Is your third floor inside the roof?";

test("AnswerList answers once, by click", async () => {
  const onAnswer = vi.fn();
  render(<GuideTheme><AnswerList question={Q} answers={ANSWERS} onAnswer={onAnswer} /></GuideTheme>);
  const group = screen.getByRole("radiogroup", { name: Q });
  await userEvent.click(within(group).getByRole("radio", { name: /Yes, inside the roof/ }));
  expect(onAnswer).toHaveBeenCalledOnce();
  expect(onAnswer).toHaveBeenCalledWith("yes");
});

test("AnswerList: arrows move the choice, Enter or Space answers", async () => {
  const onAnswer = vi.fn();
  render(<GuideTheme><AnswerList question={Q} answers={ANSWERS} onAnswer={onAnswer} /></GuideTheme>);
  await userEvent.tab();
  await userEvent.keyboard("{ArrowDown}");
  expect(onAnswer).not.toHaveBeenCalled();
  await userEvent.keyboard("{Enter}");
  expect(onAnswer).toHaveBeenCalledOnce();
  expect(onAnswer).toHaveBeenCalledWith("no");
  await userEvent.keyboard("{ArrowDown}");
  await userEvent.keyboard(" ");
  expect(onAnswer).toHaveBeenLastCalledWith("unsure");
  expect(onAnswer).toHaveBeenCalledTimes(2);
});

test("AnswerList shows each hint", () => {
  render(<GuideTheme><AnswerList question={Q} answers={ANSWERS} onAnswer={() => {}} /></GuideTheme>);
  expect(screen.getByText("like a finished attic")).toBeInTheDocument();
});
