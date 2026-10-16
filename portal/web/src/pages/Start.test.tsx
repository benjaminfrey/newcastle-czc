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
        <Route path="/where" element={<p>Where page</p>} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => sessionStorage.clear());

describe("Start", () => {
  it("asks floor area and homes only when building", async () => {
    renderPage();
    expect(screen.queryByLabelText(/How much floor area/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: "Build something new or add on" }));
    expect(screen.getByLabelText(/How much floor area/)).toBeInTheDocument();
    expect(screen.getByLabelText(/How many homes/)).toBeInTheDocument();
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
    await userEvent.type(screen.getByLabelText(/How much floor area/), "2400");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()).toMatchObject({ project: ["build", "use"], building: { gross_floor_area_sf: 2400 } });
  });

  it("leaves floor area unknown when left blank", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "Build something new or add on" }));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Where page")).toBeInTheDocument();
    expect(loadAnswers()?.building.gross_floor_area_sf).toBeNull();
  });

  it("requires at least one choice", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText(/Choose at least one/)).toBeInTheDocument();
    expect(loadAnswers()).toBeNull();
  });
});
