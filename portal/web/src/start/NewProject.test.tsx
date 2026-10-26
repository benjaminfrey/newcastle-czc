import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import type { Facts } from "../api";
import * as apps from "../projects";
import NewProject, { defaultTitle } from "./NewProject";

vi.mock("../components/ParcelMap", () => ({
  default: ({ onPick }: { onPick: (lon: number, lat: number) => void }) => (
    <button type="button" onClick={() => onPick(-69.579, 44.041)}>tap the map</button>
  ),
}));

const FACTS = {
  parcel_id: 229, map_lot: "004-036", location: "SHEEPSCOT ROAD", acres: 2.73,
  districts: [{ code: "D2", name: "Neighborhood Residential (D2)", in_ruleset: true, share: 1 }],
  streets: [], on_state_highway: false,
  as_of: { parcels: "2012-04-01", parcels_source: "Maine GeoLibrary", districts_source: null },
  geometry: { type: "MultiPolygon", coordinates: [] },
} as unknown as Facts;
const PARTS: apps.PartDef[] = [
  { id: "building", label: "A new building", step: "New buildings", icon: "building-cottage", repeats: true },
  { id: "driveway", label: "A driveway", step: "Driveway", icon: "road", repeats: false },
];

function renderFlow() {
  render(<MemoryRouter initialEntries={["/new"]}><Routes>
    <Route path="/new" element={<NewProject />} />
    <Route path="/projects/:id" element={<p>Dashboard</p>} />
  </Routes></MemoryRouter>);
}

async function pickTheLot() {
  await userEvent.click(await screen.findByRole("button", { name: "tap the map" }));
  await userEvent.click(await screen.findByRole("radio", { name: "Yes, this is my property" }));
}

beforeEach(() => {
  vi.spyOn(api, "getDistricts").mockResolvedValue([]);
  vi.spyOn(api, "parcelAt").mockResolvedValue(229);
  vi.spyOn(api, "getProperty").mockResolvedValue(FACTS);
  vi.spyOn(apps, "getParts").mockResolvedValue(PARTS);
});

describe("New application", () => {
  it("asks how to reach you, saves it to the account, then asks where", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant", name: null, phone: null, mailing_address: null });
    const put = vi.spyOn(api, "putMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    renderFlow();
    expect(await screen.findByRole("heading", { name: "How can the Town reach you?" })).toBeInTheDocument();
    expect(screen.getByText("New application")).toBeInTheDocument();
    expect(screen.getByText("1 of 3")).toBeInTheDocument();
    expect(screen.getByText("a@example.com")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Full name"), "Ada Lovelace");
    await userEvent.type(screen.getByLabelText("Phone"), "207-555-0100");
    await userEvent.type(screen.getByLabelText("Mailing address"), "PO Box 7, Newcastle ME 04553");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(put).toHaveBeenCalledWith({ name: "Ada Lovelace", phone: "207-555-0100", mailing_address: "PO Box 7, Newcastle ME 04553" });
    expect(await screen.findByText("2 of 3")).toBeInTheDocument();
  });

  it("asks for all three before going on", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant", name: "Ada", phone: null, mailing_address: null });
    const put = vi.spyOn(api, "putMe");
    renderFlow();
    await userEvent.click(await screen.findByRole("button", { name: "Continue" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Please give a phone number and a mailing address.");
    expect(put).not.toHaveBeenCalled();
  });

  it("skips the first card when the account already has the details", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant", name: "Ada", phone: "207", mailing_address: "PO Box 1" });
    renderFlow();
    expect(await screen.findByText("2 of 3")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "How can the Town reach you?" })).not.toBeInTheDocument();
  });

  it("needs a part, then creates the project and opens it", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant", name: "Ada", phone: "207", mailing_address: "PO Box 1" });
    const create = vi.spyOn(apps, "createProject").mockResolvedValue({ id: "p1" });
    renderFlow();
    await pickTheLot();
    expect(await screen.findByRole("heading", { name: "What are you doing here?" })).toBeInTheDocument();
    expect(screen.getByText("Choose all that apply. You can add more later.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Go to my project" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Choose at least one.");
    expect(create).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("checkbox", { name: "A new building" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "A driveway" }));
    await userEvent.click(screen.getByRole("button", { name: "Go to my project" }));
    expect(await screen.findByText("Dashboard")).toBeInTheDocument();
    expect(create).toHaveBeenCalledWith({ property: { source: "lookup", parcel_id: 229 }, disputed: false, note: "",
                                          parts: ["building", "driveway"], title: "A new building and a driveway at Sheepscot Road" });
  });

  it("Back from the parts goes back to the lot", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant", name: "Ada", phone: "207", mailing_address: "PO Box 1" });
    renderFlow();
    await pickTheLot();
    await userEvent.click(await screen.findByRole("button", { name: "Back" }));
    expect(await screen.findByText("2 of 3")).toBeInTheDocument();
  });
});

describe("defaultTitle", () => {
  it("joins the parts with and, lower-cased after the first, and adds the street", () => {
    expect(defaultTitle(["A new building", "A driveway", "Divide land"], "SHEEPSCOT ROAD"))
      .toBe("A new building, a driveway and divide land at Sheepscot Road");
    expect(defaultTitle(["Start or change a use"], null)).toBe("Start or change a use");
  });
});
