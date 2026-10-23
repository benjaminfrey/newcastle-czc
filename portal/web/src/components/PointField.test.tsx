import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import PointField from "./PointField";

vi.mock("./ParcelMap", () => ({
  default: ({ onPick }: { onPick: (lon: number, lat: number) => void }) => (
    <button type="button" onClick={() => onPick(-69.55, 44.05)}>tap the map</button>
  ),
}));

describe("PointField", () => {
  it("saves the tapped point", async () => {
    const onChange = vi.fn();
    render(<PointField label="Tap the map where the driveway will meet the road." parcelId={null} value={null} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "tap the map" }));
    expect(onChange).toHaveBeenCalledWith({ lon: -69.55, lat: 44.05 });
  });
});
