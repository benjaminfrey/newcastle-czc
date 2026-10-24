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

beforeEach(() => sessionStorage.clear());

describe("Start", () => {
  it("asks what kind of building work, and the right size question for it", async () => {
    renderPage();
    expect(screen.queryByLabelText(/How much floor area/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: "Build something new or add on" }));
    await userEvent.click(screen.getByRole("radio", { name: "A new building" }));
    expect(screen.getByLabelText(/How much floor area will the new building have/)).toBeInTheDocument();
    expect(screen.getByLabelText(/How many new homes/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Renovating a building" }));
    expect(screen.getByLabelText(/floor area of the whole building/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Work on the site only (parking, grading, landscaping)" }));
    expect(screen.getByLabelText(/How many parking spaces/)).toBeInTheDocument();
  });

  it("asks what kind of building work before going on", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "Build something new or add on" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText(/Choose what kind of building work/)).toBeInTheDocument();
  });

  it("understands numbers written with commas or units", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "Build something new or add on" }));
    await userEvent.click(screen.getByRole("radio", { name: "A new building" }));
    await userEvent.type(screen.getByLabelText(/How much floor area/), "2,400 sq ft");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.building.gross_floor_area_sf).toBe(2400);
  });

  it("explains a count that isn't a whole number", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "Build something new or add on" }));
    await userEvent.click(screen.getByRole("radio", { name: "A new building" }));
    await userEvent.type(screen.getByLabelText(/How many new homes/), "2.5");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText(/whole number/)).toBeInTheDocument();
    expect(loadAnswers()).toBeNull();
  });

  it("asks how many lots only when dividing land", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "Divide land" }));
    expect(screen.getByLabelText(/How many lots/)).toBeInTheDocument();
  });

  it("keeps the answers for the next step", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "Build something new or add on" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Start a business or change how a building is used" }));
    await userEvent.click(screen.getByRole("radio", { name: "A new building" }));
    await userEvent.type(screen.getByLabelText(/How much floor area/), "2400");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()).toMatchObject({ project: ["build", "use"], building: { kind: "new", gross_floor_area_sf: 2400 } });
  });

  it("leaves floor area unknown when left blank", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "Build something new or add on" }));
    await userEvent.click(screen.getByRole("radio", { name: "A new building" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.building.gross_floor_area_sf).toBeNull();
  });

  it("requires at least one choice", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText(/Choose at least one/)).toBeInTheDocument();
    expect(loadAnswers()).toBeNull();
  });

  it("asks about homes added in the last five years", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "Build something new or add on" }));
    await userEvent.click(screen.getByRole("radio", { name: "A new building" }));
    await userEvent.type(screen.getByLabelText(/How many new homes/), "1");
    await userEvent.type(screen.getByLabelText(/added on this lot in the last five years/), "2");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.building).toMatchObject({ new_dwelling_units: 1, homes_added_last_5_years: 2 });
  });

  it("asks whether the land was divided in the last five years", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "Divide land" }));
    await userEvent.type(screen.getByLabelText(/How many lots/), "2");
    await userEvent.click(screen.getByRole("radio", { name: "Yes" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.division).toEqual({ lots_after: 2, divided_last_5_years: true });
  });

  it("leaves earlier divisions unknown by default", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "Divide land" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.division.divided_last_5_years).toBeNull();
  });
});
