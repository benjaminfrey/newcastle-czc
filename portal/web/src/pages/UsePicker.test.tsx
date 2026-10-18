import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { loadAnswers, saveAnswers } from "../screener";
import UsePicker from "./UsePicker";

const GROUPS: api.UseGroup[] = [
  { key: "transport_utilities", plain: "Transport, parking and utilities", uses: [
    { use_key: "dispatch_service", code_name: "Dispatch Service", example: "A base for taxis, ambulances, tow trucks or buses.",
      definition: "The storage and dispatch of ambulances, taxis, limousines, armored cars, tow trucks, buses, and similar vehicles." },
  ] },
  { key: "food_lodging", plain: "Food, drink or places to stay", uses: [
    { use_key: "restaurant_cafe", code_name: "Restaurant & Cafe", example: "A restaurant, cafe or takeaway.",
      definition: "A business where food and beverages are prepared and served to patrons." },
  ] },
];

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/start/use"]}>
      <Routes>
        <Route path="/start/use" element={<UsePicker />} />
        <Route path="/start/results" element={<p>Results page</p>} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  sessionStorage.clear();
  saveAnswers({ project: ["use"], use_key: null, building: { kind: null, gross_floor_area_sf: null, total_floor_area_sf: null, parking_spaces: null, new_dwelling_units: null, homes_added_last_5_years: null },
                division: { lots_after: null, divided_last_5_years: null } });
});

describe("UsePicker", () => {
  it("shows the groups and finds a use by search", async () => {
    vi.spyOn(api, "getUseGroups").mockResolvedValue(GROUPS);
    renderPage();
    expect(await screen.findByRole("button", { name: "Transport, parking and utilities" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Search uses"), "taxi");
    expect(screen.getByText("Dispatch Service")).toBeInTheDocument();
    expect(screen.queryByText("Restaurant & Cafe")).not.toBeInTheDocument();
  });

  it("shows the Code's definition word for word", async () => {
    vi.spyOn(api, "getUseGroups").mockResolvedValue(GROUPS);
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Food, drink or places to stay" }));
    expect(screen.getByText("A business where food and beverages are prepared and served to patrons.")).toBeInTheDocument();
    expect(screen.getByText("What the Code says")).toBeInTheDocument();
  });

  it("saves the chosen use and moves on", async () => {
    vi.spyOn(api, "getUseGroups").mockResolvedValue(GROUPS);
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Food, drink or places to stay" }));
    await userEvent.click(screen.getByRole("button", { name: "Choose Restaurant & Cafe" }));
    expect(await screen.findByText("Results page")).toBeInTheDocument();
    expect(loadAnswers()?.use_key).toBe("restaurant_cafe");
  });

  it("says when the list isn't approved yet", async () => {
    vi.spyOn(api, "getUseGroups").mockResolvedValue("not_approved");
    renderPage();
    expect(await screen.findByText(/isn't ready yet/)).toBeInTheDocument();
  });
});
