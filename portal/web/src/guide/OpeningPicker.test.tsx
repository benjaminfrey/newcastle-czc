import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import type { Opening } from "./api";
import { OpeningPicker } from "./OpeningPicker";
import { GuideTheme } from "./theme/GuideTheme";

const o = (id: string, label: string, picture: string, guided: boolean, part: string | null, in_project: boolean): Opening =>
  ({ id, label, picture, guided, part, in_project });
const OPENINGS = [
  o("new_house", "A new house", "house_outline", true, "building", true),
  o("change_of_use", "A change of use", "barn", true, "use", false),
  o("addition", "An addition", "addition", false, null, false),
  o("deck", "A deck", "deck", false, null, false),
  o("solar", "Solar panels", "solar", false, null, false),
  o("outbuilding", "A garage, barn or shed", "shed", false, null, false),
  o("driveway", "A driveway", "driveway", false, null, false),
  o("fence_or_wall", "A fence or wall", "wall", false, null, false),
  o("sign", "A sign", "sign", false, null, false),
  o("home_business", "A business at home", "shingle", false, null, false),
];

function picker(onStart = vi.fn(async () => true), busy = false) {
  const view = render(<GuideTheme><OpeningPicker openings={OPENINGS} busy={busy} onStart={onStart} /></GuideTheme>);
  return { onStart, view };
}
const list = () => screen.getByRole("list", { name: "Or choose from the list" });
const tapSpot = (picture: string) => fireEvent.click(document.querySelector(`[data-spot="${picture}"] circle[data-hit]`)!);

test("a guided project already in the project starts at once", async () => {
  const { onStart } = picker();
  await userEvent.click(within(list()).getByRole("button", { name: "A new house" }));
  expect(onStart).toHaveBeenCalledWith("new_house", {});
});

test("a guided project not in the project asks to add it first", async () => {
  const { onStart } = picker();
  tapSpot("barn");
  const dialog = await screen.findByRole("dialog", { name: "Add a change of use to this project?" });
  await userEvent.click(within(dialog).getByRole("button", { name: "Add it" }));
  expect(onStart).toHaveBeenCalledWith("change_of_use", { addPart: "use" });
});

test("not now closes the question and starts nothing", async () => {
  const { onStart } = picker();
  tapSpot("barn");
  await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Not now" }));
  await vi.waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(onStart).not.toHaveBeenCalled();
});

test("a project the guide doesn't cover yet says coming soon", async () => {
  const { onStart } = picker();
  await userEvent.click(within(list()).getByRole("button", { name: "A deck" }));
  const dialog = await screen.findByRole("dialog", { name: "A deck: coming soon" });
  await userEvent.click(within(dialog).getByRole("button", { name: "OK" }));
  expect(onStart).not.toHaveBeenCalled();
});

test("the list offers the same projects as the scene, in the openings' order", () => {
  picker();
  expect(within(list()).getAllByRole("button").map((b) => b.textContent)).toEqual(OPENINGS.map((x) => x.label));
  const spots = [...document.querySelectorAll("[data-spot]")].map((g) => g.getAttribute("data-spot"));
  expect(new Set(spots)).toEqual(new Set(OPENINGS.map((x) => x.picture)));
});

test("the box's text survives coming soon and goes with the start", async () => {
  const { onStart } = picker();
  const box = screen.getByRole("textbox", { name: "In your own words, what would you like to do? (optional)" });
  await userEvent.type(box, "A porch on the front");
  await userEvent.click(within(list()).getByRole("button", { name: "A deck" }));
  await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "OK" }));
  await vi.waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(box).toHaveValue("A porch on the front");
  await userEvent.click(within(list()).getByRole("button", { name: "A new house" }));
  expect(onStart).toHaveBeenCalledTimes(1);
  expect(onStart).toHaveBeenCalledWith("new_house", { note: "A porch on the front" });
});

test("a second tap while adding is ignored", async () => {
  const onStart = vi.fn(() => new Promise<boolean>(() => {}));
  picker(onStart);
  tapSpot("barn");
  const yes = within(await screen.findByRole("dialog")).getByRole("button", { name: "Add it" });
  await userEvent.click(yes);
  fireEvent.click(yes);
  expect(onStart).toHaveBeenCalledTimes(1);
  expect(yes).toBeDisabled();
});

test("while the guide is busy the list can't be tapped", () => {
  picker(undefined, true);
  for (const b of within(list()).getAllByRole("button")) expect(b).toBeDisabled();
});
