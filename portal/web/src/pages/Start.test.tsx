import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import { loadAnswers } from "../screener";
import Start from "./Start";

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/start"]}>
      <Routes>
        <Route path="/start" element={<Start />} />
        <Route path="/start/property" element={<p>Where page</p>} />
      </Routes>
    </MemoryRouter>,
  );
const cont = () => userEvent.click(screen.getByRole("button", { name: /^(Continue|Skip for now)$/ }));
const choose = (...names: string[]) => Promise.all(names.map((n) => userEvent.click(screen.getByRole("checkbox", { name: n }))));
const BUILD = "Build something new or add on";

async function newBuilding() {
  renderPage();
  await userEvent.click(screen.getByRole("checkbox", { name: BUILD }));
  await cont();
  await userEvent.click(await screen.findByRole("radio", { name: "A new building" }));
  await screen.findByRole("textbox", { name: /How much floor area/ }); // the tap moves on after a moment
}

beforeEach(() => sessionStorage.clear());

describe("Start, one question at a time", () => {
  it("What are you planning? is choose-several, with Continue", async () => {
    renderPage();
    expect(screen.getByRole("heading", { name: "What are you planning?" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Divide land" })).toBeInTheDocument();
    await cont();
    expect(await screen.findByText(/Choose at least one/)).toBeInTheDocument();
    expect(loadAnswers()).toBeNull();
  });

  it("building work is a tap, and the floor area follows", async () => {
    renderPage();
    await choose(BUILD);
    await cont();
    await screen.findByRole("radio", { name: "A new building" });
    expect(screen.queryByRole("button", { name: /^(Continue|Skip for now)$/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "A new building" }));
    expect(await screen.findByRole("textbox", { name: /How much floor area will the new building have/ })).toBeInTheDocument();
  });

  it("the floor area shows only for building work", async () => {
    renderPage();
    await choose("Start a business or change how a building is used");
    await cont();
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.building.gross_floor_area_sf).toBeNull();
  });

  it("asks the size question that fits the work", async () => {
    renderPage();
    await choose(BUILD);
    await cont();
    await userEvent.click(await screen.findByRole("radio", { name: "Renovating a building" }));
    expect(await screen.findByRole("textbox", { name: /floor area of the whole building/ })).toBeInTheDocument();
  });

  it("asks for parking spaces for site work", async () => {
    renderPage();
    await choose(BUILD);
    await cont();
    await userEvent.click(await screen.findByRole("radio", { name: "Work on the site only (parking, grading, landscaping)" }));
    expect(await screen.findByRole("textbox", { name: /How many parking spaces/ })).toBeInTheDocument();
  });

  it("understands numbers written with commas", async () => {
    await newBuilding();
    await userEvent.type(await screen.findByRole("textbox", { name: /How much floor area/ }), "2,400");
    await cont(); await cont(); await cont();
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.building.gross_floor_area_sf).toBe(2400);
  });

  it("steps a home count up and down, never below zero, a whole number", async () => {
    await newBuilding();
    await cont();
    const more = await screen.findByRole("button", { name: /Increase How many new homes/ });
    await userEvent.click(more); await userEvent.click(more); await userEvent.click(more);
    await userEvent.click(screen.getByRole("button", { name: /Decrease How many new homes/ }));
    await cont(); await cont();
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.building.new_dwelling_units).toBe(1); // blank, then 0, 1, 2, back to 1
    expect(Number.isInteger(loadAnswers()?.building.new_dwelling_units)).toBe(true);
  });

  it("keeps the answers for the next step", async () => {
    renderPage();
    await choose(BUILD, "Start a business or change how a building is used");
    await cont();
    await userEvent.click(await screen.findByRole("radio", { name: "A new building" }));
    await userEvent.type(await screen.findByRole("textbox", { name: /How much floor area/ }), "2400");
    await cont(); await cont(); await cont();
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()).toMatchObject({ project: ["build", "use"], building: { kind: "new", gross_floor_area_sf: 2400 } });
  });

  it("a blank floor area is Skip for now, and stays unknown", async () => {
    await newBuilding();
    await screen.findByRole("textbox", { name: /How much floor area/ });
    expect(screen.getByRole("button", { name: "Skip for now" })).toBeInTheDocument();
    await cont(); await cont(); await cont();
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.building.gross_floor_area_sf).toBeNull();
  });

  it("asks about homes added in the last five years", async () => {
    await newBuilding();
    await cont();
    const newHomes = await screen.findByRole("button", { name: /Increase How many new homes/ });
    await userEvent.click(newHomes); await userEvent.click(newHomes);
    await cont();
    const earlier = await screen.findByRole("button", { name: /Increase How many homes were added/ });
    await userEvent.click(earlier); await userEvent.click(earlier); await userEvent.click(earlier);
    await cont();
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.building).toMatchObject({ new_dwelling_units: 1, homes_added_last_5_years: 2 });
  });

  it("asks whether the land was divided in the last five years, as a tap", async () => {
    renderPage();
    await choose("Divide land");
    await cont();
    const more = await screen.findByRole("button", { name: /Increase How many lots/ });
    await userEvent.click(more); await userEvent.click(more);
    await cont();
    await userEvent.click(await screen.findByRole("radio", { name: "Yes" }));
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.division).toEqual({ lots_after: 2, divided_last_5_years: true });
  });

  it("I don't know leaves earlier divisions unknown", async () => {
    renderPage();
    await choose("Divide land");
    await cont(); await cont();
    await userEvent.click(await screen.findByRole("radio", { name: "I don't know" }));
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.division.divided_last_5_years).toBeNull();
  });

  it("the card's bar counts the questions that apply, and Back goes back", async () => {
    await newBuilding();
    expect(screen.getByRole("img", { name: /^Question 3 of / })).toBeInTheDocument();
    expect(screen.getByText("Your project")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(await screen.findByRole("radio", { name: "A new building" })).toHaveAttribute("aria-checked", "true");
  });

  it("every plan tile has its icon, and there's no line of intro", () => {
    renderPage();
    for (const name of [BUILD, /Start a business/, /driveway/, "Divide land", /Something else/]) {
      expect(screen.getByRole("checkbox", { name }).querySelector("svg")).not.toBeNull();
    }
    expect(screen.queryByText(/Answer a few questions/)).not.toBeInTheDocument();
  });

  it("the kinds of building work have icons too", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: BUILD }));
    await cont();
    expect((await screen.findByRole("radio", { name: "A new building" })).querySelector("svg")).not.toBeNull();
  });

  it("the bar doesn't shrink when a later answer removes questions", async () => {
    await newBuilding();
    const before = screen.getByRole("img", { name: /^Question 3 of / }).getAttribute("aria-label")!;
    const total = Number(before.split(" of ")[1]);
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    await userEvent.click(await screen.findByRole("radio", { name: "Work on the site only (parking, grading, landscaping)" }));
    const after = await screen.findByRole("img", { name: /^Question 3 of / });
    expect(Number(after.getAttribute("aria-label")!.split(" of ")[1])).toBeGreaterThanOrEqual(total);
  });
});
