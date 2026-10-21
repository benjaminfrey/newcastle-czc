import { Label } from "@heroui/react";
import { useEffect, useState } from "react";
import { getProperty, type Facts } from "../api";
import ParcelMap from "./ParcelMap";

type Point = { lon: number; lat: number };
type Props = { label: string; parcelId: number | null; value: Point | null; onChange: (p: Point) => void };

// A tap on the map, with the applicant's lot outlined when the Town's map knows it.
export default function PointField({ label, parcelId, value, onChange }: Props) {
  const [lot, setLot] = useState<Facts["geometry"] | null>(null);

  useEffect(() => {
    if (parcelId === null) return;
    getProperty(parcelId).then((f) => {
      if (f && typeof f === "object") setLot(f.geometry);
    });
  }, [parcelId]);

  return (
    <div className="flex flex-col gap-2">
      <Label>{label}</Label>
      <ParcelMap selected={lot} focus={null} pin={value} onPick={(lon, lat) => onChange({ lon, lat })} />
      <p className="text-sm" aria-live="polite">{value ? "Marked. Tap again to move the mark." : "Nothing marked yet."}</p>
    </div>
  );
}
