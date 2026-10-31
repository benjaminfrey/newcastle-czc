import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { ReplyBox } from "./ReplyBox";

test("send is disabled while the box is blank", async () => {
  render(<GuideTheme><ReplyBox placeholder="Or tell us more…" onSend={() => {}} /></GuideTheme>);
  const send = screen.getByRole("button", { name: "Send" });
  expect(send).toBeDisabled();
  await userEvent.type(screen.getByRole("textbox", { name: "Or tell us more…" }), "   ");
  expect(send).toBeDisabled();
});

test("Enter sends the text and clears the box", async () => {
  const onSend = vi.fn();
  render(<GuideTheme><ReplyBox placeholder="Or tell us more…" onSend={onSend} /></GuideTheme>);
  const box = screen.getByRole("textbox", { name: "Or tell us more…" });
  await userEvent.type(box, "It's a cape{Enter}");
  expect(onSend).toHaveBeenCalledWith("It's a cape");
  expect(box).toHaveValue("");
});

test("the reply box is full size, not the small field", () => {
  render(<GuideTheme><ReplyBox placeholder="Or tell us more…" onSend={() => {}} /></GuideTheme>);
  expect(document.querySelector(".MuiInputBase-sizeSmall")).toBeNull();
});
