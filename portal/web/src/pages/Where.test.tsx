import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import type { Facts } from "../api";
import { loadProperty } from "../property";
import Where from "./Where";

// jsdom has no WebGL: a stand-in map that "taps" a point when its button is pressed.
vi.mock("../components/ParcelMap", () => ({
  default: ({ onPick }: { onPick: (lon: number, lat: number) => void }) => (
    <button type="button" onClick={() => onPick(-69.579, 44.041)}>tap the map</button>
  ),
}));

const FACTS: Facts = {
  parcel_id: 229,
  map_lot: "004-036",
  location: "SHEEPSCOT ROAD",
  acres: 2.73,
  districts: [
    { code: "D2", name: "Neighborhood Residential (D2)", in_ruleset: true, share: 0.75 },
    { code: "D1", name: "Rural (D1)", in_ruleset: true, share: 0.25 },
  ],
  streets: [{ name: "Sheepscot Road", type: "R1", type_name: "Connector Road", ownership: "Town Way", frontage_ft: 675 }],
  on_state_highway: false,
  as_of: { parcels: "2012-04-01", parcels_source: "Maine GeoLibrary", districts_source: "Traced; approximate" },
  geometry: { type: "MultiPolygon", coordinates: [[[[-69.6, 44.04], [-69.59, 44.04], [-69.59, 44.05], [-69.6, 44.04]]]] },
};

const onDone = vi.fn();
const renderPage = () => render(<MemoryRouter><Where onDone={onDone} /></MemoryRouter>);

async function search(text: string) {
  await userEvent.type(screen.getByLabelText("Street address, or map and lot"), text);
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
}

beforeEach(() => {
  sessionStorage.clear();
  onDone.mockReset();
  vi.spyOn(api, "getDistricts").mockResolvedValue([
    { code: "D1", name: "Rural (D1)" }, { code: "D2", name: "Neighborhood Residential (D2)" }]);
});

describe("Where", () => {
  it("shows the lot, districts, size, street and the map's date after picking a search result", async () => {
    vi.spyOn(api, "searchProperty").mockResolvedValue([{ label: "461 Sheepscot Road", lon: -69.6, lat: 44.04, parcel_id: 229 }]);
    const get = vi.spyOn(api, "getProperty").mockResolvedValue(FACTS);
    renderPage();
    await search("461 Sheepscot");
    await userEvent.click(await screen.findByRole("button", { name: "461 Sheepscot Road" }));
    expect(get).toHaveBeenCalledWith(229);
    expect(await screen.findByText("Map 4, Lot 36")).toBeInTheDocument();
    expect(screen.getByText(/more than one district/)).toBeInTheDocument();
    expect(screen.getByText(/Neighborhood Residential \(D2\) \(most of it\)/)).toBeInTheDocument();
    expect(screen.getByText(/About 2.73 acres \(measured from the map\)/)).toBeInTheDocument();
    expect(screen.getByText(/About 675 ft along Sheepscot Road, a Connector Road/)).toBeInTheDocument();
    expect(screen.getByText(/as of April 1, 2012/)).toBeInTheDocument();
    expect(screen.getByText(/Code Enforcement Officer confirms/)).toBeInTheDocument();
  });

  it("says when part of a lot is in an area staff will confirm", async () => {
    vi.spyOn(api, "parcelAt").mockResolvedValue(229);
    vi.spyOn(api, "getProperty").mockResolvedValue({
      ...FACTS,
      districts: [{ code: "D1", name: "Rural (D1)", in_ruleset: true, share: 0.5 },
                  { code: "SD-Unmapped", name: null, in_ruleset: false, share: 0.5 }],
    });
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "tap the map" }));
    expect(await screen.findByText(/an area staff will confirm/)).toBeInTheDocument();
    expect(screen.queryByText(/Unmapped/)).not.toBeInTheDocument();
  });

  it("explains that only the Town builds on Civic land", async () => {
    vi.spyOn(api, "parcelAt").mockResolvedValue(229);
    vi.spyOn(api, "getProperty").mockResolvedValue({
      ...FACTS,
      districts: [{ code: "SD-Civic", name: "Civic district (Town-owned land)", in_ruleset: true, share: 1 }],
    });
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "tap the map" }));
    expect(await screen.findByText(/^Civic district \(Town-owned land\)/)).toBeInTheDocument();
    expect(screen.getByText(/Only the Town builds on Civic land/)).toBeInTheDocument();
    expect(screen.getByText(/Town Meeting/)).toBeInTheDocument();
  });

  it("asks for a tap when the address has no lot", async () => {
    vi.spyOn(api, "searchProperty").mockResolvedValue([{ label: "12 Main Street", lon: -69.58, lat: 44.03, parcel_id: null }]);
    renderPage();
    await search("12 Main");
    await userEvent.click(await screen.findByRole("button", { name: "12 Main Street" }));
    expect(await screen.findByText(/found that address but not the lot/)).toBeInTheDocument();
  });

  it("finds the lot from a tap on the map", async () => {
    const at = vi.spyOn(api, "parcelAt").mockResolvedValue(229);
    vi.spyOn(api, "getProperty").mockResolvedValue(FACTS);
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "tap the map" }));
    expect(at).toHaveBeenCalledWith(-69.579, 44.041);
    expect(await screen.findByText("Map 4, Lot 36")).toBeInTheDocument();
  });

  it("the lot found is its own screen: Is this your property?", async () => {
    vi.spyOn(api, "parcelAt").mockResolvedValue(229);
    vi.spyOn(api, "getProperty").mockResolvedValue(FACTS);
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "tap the map" }));
    expect(await screen.findByRole("heading", { name: "Is this your property?" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Street address, or map and lot")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "No, search again" }));
    expect(await screen.findByLabelText("Street address, or map and lot")).toBeInTheDocument();
  });

  it("asks in the card's voice: a 20 px question, and the near-black button", async () => {
    renderPage();
    expect(screen.getByRole("heading", { name: "Where is the property?" })).toHaveClass("text-[20px]");
    expect(screen.getByRole("button", { name: "Search" })).toHaveClass("btn-filled");
  });

  it("says so when nothing is at the tapped spot", async () => {
    vi.spyOn(api, "parcelAt").mockResolvedValue(null);
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "tap the map" }));
    expect(await screen.findByText(/no lot at that spot/)).toBeInTheDocument();
  });

  it("saves the property when the person confirms it", async () => {
    vi.spyOn(api, "parcelAt").mockResolvedValue(229);
    vi.spyOn(api, "getProperty").mockResolvedValue(FACTS);
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "tap the map" }));
    await userEvent.click(await screen.findByRole("radio", { name: "Yes, this is my property" }));
    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(loadProperty()).toEqual({ source: "lookup", parcel_id: 229, map_lot: "004-036", district_code: "D2",
                                     district_codes: ["D2", "D1"], on_state_highway: false,
                                     disputed: false, note: "", as_of: "2012-04-01" });
  });

  it("records what looks wrong without blocking", async () => {
    vi.spyOn(api, "parcelAt").mockResolvedValue(229);
    vi.spyOn(api, "getProperty").mockResolvedValue(FACTS);
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "tap the map" }));
    await userEvent.click(await screen.findByRole("radio", { name: "This doesn't look right" }));
    await userEvent.type(screen.getByLabelText("What looks wrong?"), "The lot was split in 2019");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(loadProperty()).toMatchObject({ source: "lookup", parcel_id: 229, disputed: true, note: "The lot was split in 2019" });
  });

  it("falls back to entering it by hand when lookup is unavailable", async () => {
    vi.spyOn(api, "searchProperty").mockResolvedValue("unavailable");
    renderPage();
    await search("461 Sheepscot");
    expect(await screen.findByText(/can't look up properties right now/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Map and lot"), "4-36");
    await userEvent.click(screen.getByRole("radio", { name: "Rural (D1)" }));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(loadProperty()).toMatchObject({ source: "manual", parcel_id: null, map_lot: "4-36", district_code: "D1",
                                           district_codes: ["D1"], on_state_highway: null });
  });

  it("offers manual entry when the person can't find their property", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "I can't find my property" }));
    expect(screen.getByLabelText("Map and lot")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "I'm not sure" })).toBeInTheDocument();
  });

  it("asks the person to wait when lookups are rate-limited", async () => {
    vi.spyOn(api, "searchProperty").mockResolvedValue("busy");
    renderPage();
    await search("461 Sheepscot");
    expect(await screen.findByText(/wait a minute/)).toBeInTheDocument();
    expect(screen.queryByText(/couldn't find that/)).not.toBeInTheDocument();
  });
});
