import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import type { FormField } from "../applications";
import * as storeModule from "../app/ApplicationStore";
import { buildingLabel } from "./pickers";
import FieldControl, { controlFor } from "./FieldControl";

vi.mock("../components/ParcelMap", () => ({
  default: ({ onPick }: { onPick: (lon: number, lat: number) => void }) =>
    <button type="button" onClick={() => onPick(-69.55, 44.05)}>tap the map</button>,
}));

const f = (extra: Partial<FormField>): FormField => ({
  id: "x", official_label: "X", source: "question", from: null, may_correct: false, label: "A question?", help: null,
  why: null, type: "text", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null,
  options: [], step: "s", page: null, control: null, step_size: null, default: null, autocomplete: null, ...extra,
});
const opts = (...v: string[]) => v.map((x) => ({ value: x, label: x.toUpperCase(), official: x }));

function fakeStore(over: Partial<ReturnType<typeof storeModule.useApplication>> = {}) {
  const store = {
    app: { id: "app1", attachments: [], items: [], property: { parcel_id: null } },
    form: { sections: [{ id: "building", repeat: { kind: "building" }, fields: [f({ id: "building_name" })] }] },
    cur: { answers: [], items: [], property: { streets: [{ name: "Sheepscot Road" }, { name: "Hall Street" }] }, account: {} },
    ...over,
  } as unknown as ReturnType<typeof storeModule.useApplication>;
  vi.spyOn(storeModule, "useApplication").mockReturnValue(store);
  return store;
}

const draw = (field: FormField, value: unknown = null) => {
  const onValue = vi.fn();
  render(<FieldControl field={field} itemId={null} value={value} onValue={onValue} />);
  return onValue;
};

beforeEach(() => fakeStore());

describe("FieldControl", () => {
  it.each([
    [f({ type: "number" }), "number"], [f({ type: "number", control: "stepper" }), "stepper"],
    [f({ type: "number", control: "slider" }), "slider"], [f({ type: "yesno" }), "segmented"],
    [f({ type: "yesno", control: "switch" }), "switch"], [f({ type: "choice", options: opts("a", "b") }), "segmented"],
    [f({ type: "choice", options: opts("a", "b", "c", "d", "e") }), "tiles"],
    [f({ type: "choice", control: "picker", options: opts("a") }), "picker"],
    [f({ type: "multichoice", options: opts("a") }), "chips"], [f({ type: "uses" }), "uses"],
    [f({ type: "upload" }), "upload"], [f({ type: "point" }), "point"], [f({ type: "longtext" }), "longtext"],
    [f({ type: "text" }), "text"], [f({ type: "text", control: "building-picker" }), "building-picker"],
  ])("maps each type and control to its component (%#)", (field, kind) => {
    expect(controlFor(field)).toBe(kind);
  });

  it("a typed value saves on blur, trimmed", async () => {
    const onValue = draw(f({ type: "text", autocomplete: "tel" }));
    const box = screen.getByRole("textbox", { name: "A question?" });
    expect(box).toHaveAttribute("autocomplete", "tel");
    await userEvent.type(box, " 207 555 0100 ");
    expect(onValue).not.toHaveBeenCalled();
    await userEvent.tab();
    expect(onValue).toHaveBeenCalledWith("207 555 0100");
  });

  it("offers I don't know yet only where allowed", async () => {
    draw(f({ type: "text" }));
    expect(screen.queryByRole("button", { name: "I don't know yet" })).not.toBeInTheDocument();
    const onValue = vi.fn();
    render(<FieldControl field={f({ type: "text", allow_unknown: true, id: "y" })} itemId={null} value={null} onValue={onValue} />);
    await userEvent.click(screen.getByRole("button", { name: "I don't know yet" }));
    expect(onValue).toHaveBeenCalledWith({ unknown: true });
  });

  it("shows an error under the control", () => {
    render(<FieldControl field={f({ type: "text" })} itemId={null} value={null} onValue={vi.fn()} error="Please shorten it." />);
    expect(screen.getByText("Please shorten it.")).toBeInTheDocument();
  });
});

describe("NumberControl", () => {
  it("stepper increments within min and max", async () => {
    const onValue = draw(f({ type: "number", control: "stepper", min: 0, max: 2, label: "How many homes?" }), 2);
    expect(screen.getByRole("button", { name: /increase/i })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /decrease/i }));
    expect(onValue).toHaveBeenCalledWith(1);
  });

  it("suffix shows the unit and a typed number saves on blur", async () => {
    const onValue = draw(f({ type: "number", unit: "ft", min: 0, max: 500, label: "How wide?" }));
    expect(screen.getByText("ft")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("textbox", { name: "How wide?" }), "24");
    await userEvent.tab();
    expect(onValue).toHaveBeenCalledWith(24);
  });
});

describe("NumberControl ranges", () => {
  it("a typed number outside the range goes as typed, for the form to explain, not quietly changed", async () => {
    const onValue = draw(f({ type: "number", unit: "ft", min: 0, max: 30, label: "How high?" }));
    await userEvent.type(screen.getByRole("textbox", { name: "How high?" }), "35");
    await userEvent.tab();
    expect(onValue).toHaveBeenCalledWith(35);
  });
});

describe("SliderControl", () => {
  it("an unanswered slider says so, rather than showing its lowest value as if chosen", () => {
    draw(f({ type: "number", control: "slider", min: 0, max: 100, step_size: 5, unit: "%", label: "North wall" }));
    expect(screen.getByText("Not answered yet")).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });

  it("steps by 5 and announces its value", async () => {
    const onValue = draw(f({ type: "number", control: "slider", min: 0, max: 100, step_size: 5, unit: "%", label: "North wall" }), 20);
    const thumb = screen.getByRole("slider", { name: "North wall" });
    expect(thumb).toHaveAttribute("aria-valuetext", "20%");
    thumb.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(onValue).toHaveBeenCalledWith(25);
  });
});

describe("SwitchControl", () => {
  it("saves now", async () => {
    const onValue = draw(f({ type: "yesno", control: "switch", label: "Do you own this property?" }), true);
    await userEvent.click(screen.getByRole("switch", { name: "Do you own this property?" }));
    expect(onValue).toHaveBeenCalledWith(false);
  });

  it("turns over when its track is clicked, which is what a person sees", async () => {
    const onValue = draw(f({ type: "yesno", control: "switch", label: "Do you own this property?" }), true);
    await userEvent.click(document.querySelector('[data-slot="switch-control"]')!);
    expect(onValue).toHaveBeenCalledWith(false);
  });
});

describe("SegmentedControl", () => {
  it("Yes/No are distinct from unanswered", async () => {
    const onValue = draw(f({ type: "yesno", label: "Is there a ditch?" }));
    const yes = screen.getByRole("radio", { name: "Yes" });
    expect(yes).not.toBeChecked();
    expect(screen.getByRole("radio", { name: "No" })).not.toBeChecked();
    await userEvent.click(yes);
    expect(onValue).toHaveBeenCalledWith(true);
  });
});

describe("TileControl", () => {
  it("roof tiles show silhouettes and have names", async () => {
    const field = f({ id: "roof_style", type: "choice", control: "tiles", label: "What shape is the roof?",
                      options: [{ value: "gable", label: "Gable: two slopes", official: "Gable" },
                                { value: "shed", label: "Shed: one slope", official: "Shed" }] });
    const onValue = draw(field);
    const gable = screen.getByRole("radio", { name: "Gable: two slopes" });
    expect(gable.closest("label")!.querySelector("svg")).not.toBeNull();
    await userEvent.click(gable);
    expect(onValue).toHaveBeenCalledWith("gable");
  });
});

describe("PickerControl", () => {
  it("roof slope picker saves 8_12", async () => {
    const onValue = draw(f({ type: "choice", control: "picker", label: "How steep is the roof?",
                             options: [{ value: "6_12", label: "6/12", official: "6/12" }, { value: "8_12", label: "8/12", official: "8/12" }] }));
    await userEvent.click(screen.getByRole("button", { name: /How steep is the roof\?/ }));
    await userEvent.click(await screen.findByRole("option", { name: "8/12" }));
    expect(onValue).toHaveBeenCalledWith("8_12");
  });
});

describe("ChipsControl", () => {
  it("toggles chips", async () => {
    const onValue = draw(f({ type: "multichoice", control: "chips", label: "Exterior finish?", options: opts("brick", "stone") }), ["brick"]);
    await userEvent.click(screen.getByRole("row", { name: "STONE" }));
    expect(onValue).toHaveBeenCalledWith(["brick", "stone"]);
  });
});

describe("blank lists", () => {
  it("removing the last chip saves nothing, not an empty list", async () => {
    const onValue = draw(f({ type: "multichoice", control: "chips", label: "Exterior finish?", options: opts("brick") }), ["brick"]);
    await userEvent.click(screen.getByRole("row", { name: "BRICK" }));
    expect(onValue).toHaveBeenCalledWith(null);
  });

  it("removing the last use saves nothing", async () => {
    vi.spyOn(api, "getUseGroups").mockResolvedValue([]);
    const onValue = draw(f({ type: "uses", label: "Which uses will stop?" }), ["office_small"]);
    await userEvent.click(screen.getByRole("button", { name: /Remove/ }));
    expect(onValue).toHaveBeenCalledWith(null);
  });
});

describe("No Why we ask", () => {
  it("a question with a Code citation doesn't show it", () => {
    draw(f({ type: "text", why: { cite: "8.2.a.2", text: "The Code's words." } }));
    expect(screen.queryByText("Why we ask")).not.toBeInTheDocument();
    expect(screen.queryByText(/The Code's words/)).not.toBeInTheDocument();
  });
});

describe("BuildingPicker", () => {
  it("lists this application's buildings", async () => {
    fakeStore({ cur: { answers: [{ field_id: "building_name", item_id: "b1", value: "House" }],
                       items: [{ id: "b1", kind: "building", position: 0 }], property: {}, account: {} } as never });
    const onValue = draw(f({ id: "attached_to", type: "text", control: "building-picker", label: "Which building is it attached to?" }));
    expect(screen.getByRole("radio", { name: "Free-standing" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Building 1: House" }));
    expect(onValue).toHaveBeenCalledWith("b1"); // the building itself, so a rename or a deletion can't leave stale words
  });

  it("names the chosen building as it is now", () => {
    const store = fakeStore({ cur: { answers: [{ field_id: "building_name", item_id: "b1", value: "Barn" }],
                                     items: [{ id: "b1", kind: "building", position: 0 }], property: {}, account: {} } as never });
    expect(buildingLabel(store.form!, store.cur!, "b1")).toBe("Building 1: Barn");
    expect(buildingLabel(store.form!, store.cur!, "Free-standing")).toBe("Free-standing");
    expect(buildingLabel(store.form!, store.cur!, "Building 1: House")).toBe("Building 1: House"); // an answer from before
    expect(buildingLabel(store.form!, store.cur!, "00000000-0000-0000-0000-000000000000")).toBeNull(); // deleted since
  });
});

describe("StreetPicker", () => {
  it("lists the lot's roads; Another road asks for a name", async () => {
    const onValue = draw(f({ id: "entrance_street", type: "text", control: "street-picker", label: "Which road?" }));
    await userEvent.click(screen.getByRole("radio", { name: "Hall Street" }));
    expect(onValue).toHaveBeenCalledWith("Hall Street");
    await userEvent.click(screen.getByRole("radio", { name: "Another road" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Name of the road" }), "River Road");
    await userEvent.tab();
    expect(onValue).toHaveBeenLastCalledWith("River Road");
  });
});

describe("BuildingTypeControl", () => {
  const field = f({ id: "building_class", type: "choice", control: "building-type", label: "Which best describes this building?",
    options: [
      { value: "residential", label: "A home", official: "Residential Building" },
      { value: "single_unit_commercial", label: "One business", official: "Single Unit Commercial Building" },
      { value: "multi_unit_commercial", label: "Several businesses", official: "Multi-unit Commercial Building" },
      { value: "mixed_use", label: "Homes and businesses", official: "Mixed-Use Building" },
      { value: "residential_accessory", label: "Goes with a home", official: "Residential Accessory Building" },
      { value: "commercial_accessory", label: "Goes with a business", official: "Commercial Accessory Building" },
      { value: "general_accessory", label: "Either", official: "General Accessory Building" },
      { value: "special_use", label: "Special use", official: "Special Use Building" },
      { value: "agricultural", label: "Farm building", official: "Agricultural Building" },
    ] });

  it("Home leads straight to Residential Building", async () => {
    const onValue = draw(field);
    await userEvent.click(screen.getByRole("radio", { name: "A home" }));
    expect(onValue).toHaveBeenCalledWith("residential");
  });

  it("the first step's kinds each carry an icon", () => {
    draw(field);
    for (const name of ["A home", /A building for a business/, /A smaller building/, "A farm building", "Something else"]) {
      expect(screen.getByRole("radio", { name }).querySelector("svg")).not.toBeNull();
    }
  });

  it("A smaller building asks which kind", async () => {
    const onValue = draw(field);
    await userEvent.click(screen.getByRole("radio", { name: /A smaller building/ }));
    expect(onValue).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("radio", { name: "Goes with a home" }));
    expect(onValue).toHaveBeenCalledWith("residential_accessory");
  });
});

describe("UsesControl", () => {
  it("shows chosen uses as chips and adds from the search", async () => {
    vi.spyOn(api, "getUseGroups").mockResolvedValue([{ key: "g", plain: "Shops", uses: [
      { use_key: "office_small", code_name: "Office, Small", example: "e", definition: "d" }] }]);
    const onValue = draw(f({ type: "uses", label: "Which uses?" }), []);
    await userEvent.click(screen.getByRole("button", { name: "Add a use" }));
    await userEvent.type(await screen.findByLabelText("Search uses"), "office");
    await userEvent.click(screen.getByRole("button", { name: "Add Office, Small" }));
    expect(onValue).toHaveBeenCalledWith(["office_small"]);
  });
});

describe("UploadControl", () => {
  it("offers the camera and states the limits; each button is named for its question", () => {
    draw(f({ type: "upload", label: "Add a sketch." }));
    expect(screen.getByLabelText("Take a photo or choose a file: Add a sketch.")).toBeInTheDocument();
    const input = screen.getByLabelText(/^Take a photo or choose a file/);
    expect(input).toHaveAttribute("accept", expect.stringContaining("image/*"));
    expect(screen.getByText("PDF, JPEG, PNG or HEIC · up to 25 MB")).toBeInTheDocument();
  });

  it("refuses a file over 25 MB before sending it", async () => {
    const { default: apps } = await import("../applications").then((m) => ({ default: m }));
    const spy = vi.spyOn(apps, "uploadFile");
    draw(f({ type: "upload", label: "Add a sketch." }));
    const big = new File(["x"], "photo.jpg", { type: "image/jpeg" });
    Object.defineProperty(big, "size", { value: 26_214_401 });
    await act(() => userEvent.upload(screen.getByLabelText(/^Take a photo or choose a file/), big));
    expect(await screen.findByRole("alert")).toHaveTextContent(/up to 25 MB/);
    expect(spy).not.toHaveBeenCalled();
  });

  it("hands a kept file to the application, so review and a return visit both show it", async () => {
    const apps = await import("../applications");
    vi.spyOn(apps, "uploadFile").mockResolvedValue({ id: "a1", filename: "sketch.pdf", content_type: "application/pdf", size_bytes: 2048 } as never);
    const attachmentAdded = vi.fn();
    fakeStore({ attachmentAdded } as never);
    draw(f({ id: "sketch", type: "upload", label: "Add a sketch." }));
    await act(() => userEvent.upload(screen.getByLabelText(/^Take a photo or choose a file/), new File(["x"], "sketch.pdf", { type: "application/pdf" })));
    expect(attachmentAdded).toHaveBeenCalledWith(expect.objectContaining({ id: "a1", field_id: "sketch", item_id: null }));
  });

  it("lists the files the application already holds", () => {
    fakeStore({ app: { id: "app1", items: [], property: { parcel_id: null }, attachments: [
      { id: "a1", field_id: "sketch", item_id: null, filename: "sketch.pdf", content_type: "application/pdf", size_bytes: 2048 }] } } as never);
    draw(f({ id: "sketch", type: "upload", label: "Add a sketch." }));
    expect(screen.getByRole("list", { name: "Files added" })).toHaveTextContent("sketch.pdf");
  });
});

describe("PointControl", () => {
  it("saves the tapped point", async () => {
    const onValue = draw(f({ type: "point", label: "Tap the map where the driveway meets the road." }));
    await userEvent.click(screen.getByRole("button", { name: "tap the map" }));
    expect(onValue).toHaveBeenCalledWith({ lon: -69.55, lat: 44.05 });
  });
});
