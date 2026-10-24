import { useEffect, useState } from "react";
import { getProperty, type Facts } from "../api";
import { useApplication } from "../app/ApplicationStore";
import ParcelMap from "../components/ParcelMap";

type Point = { lon: number; lat: number };

// A tap on the map of your lot (outlined when the Town's map knows it) marks the spot.
export default function PointControl({ value, onValue }: { value: unknown; onValue: (p: Point) => void }) {
  const { app } = useApplication();
  const parcelId = app?.property.parcel_id ?? null;
  const [lot, setLot] = useState<Facts["geometry"] | null>(null);
  useEffect(() => {
    if (parcelId === null) return;
    getProperty(parcelId).then((f) => { if (f && typeof f === "object") setLot(f.geometry); });
  }, [parcelId]);
  const pin = value && typeof value === "object" && "lon" in value ? (value as Point) : null;
  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-hidden rounded-xl"><ParcelMap selected={lot} focus={null} pin={pin} onPick={(lon, lat) => onValue({ lon, lat })} /></div>
      <p className="text-[15px] text-[var(--app-secondary-label)]" aria-live="polite">
        {pin ? "Marked. Tap again to move the mark." : "Nothing marked yet."}
      </p>
    </div>
  );
}
