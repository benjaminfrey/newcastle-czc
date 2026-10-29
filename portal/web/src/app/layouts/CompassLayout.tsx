import type { ReactNode } from "react";

// North, drawn: an arrow with N above it, in the label colour.
function NorthArrow() {
  return (
    <svg viewBox="0 0 40 56" className="h-14 w-10" aria-hidden="true">
      <text x="20" y="13" textAnchor="middle" fontSize="13" fontWeight="600" fill="var(--app-label)">N</text>
      <path d="M20 18 L29 46 L20 40 L11 46 Z" fill="var(--app-label)" />
    </svg>
  );
}

// The four walls' window shares around a small plan of the building, so "north" is a place on
// a picture rather than a word to work out. The street side is named when the map knows it.
export default function CompassLayout({ walls, street }: { walls: Record<"north" | "east" | "south" | "west", ReactNode>; street?: string | null }) {
  return (
    // Laid out by the space it has (a sheet is narrow even on a desktop), not by the window.
    <div className="@container flex flex-col gap-3">
      {street && <p className="text-center text-[15px] text-[var(--app-secondary-label)]">The front faces {street}</p>}
      <div className="grid grid-cols-1 gap-2 @2xl:grid-cols-[1fr_7rem_1fr] @2xl:grid-rows-[auto_7rem_auto] @2xl:items-center">
        <div className="@2xl:col-span-3 @2xl:row-start-1 @2xl:mx-auto @2xl:w-1/2">{walls.north}</div>
        <div className="@2xl:col-start-1 @2xl:row-start-2">{walls.west}</div>
        <div aria-hidden="true" className="order-first mx-auto flex size-20 items-center justify-center rounded-lg border-2 border-[var(--app-label)] @2xl:order-none @2xl:col-start-2 @2xl:row-start-2 @2xl:size-28">
          <NorthArrow />
        </div>
        <div className="@2xl:col-start-3 @2xl:row-start-2">{walls.east}</div>
        <div className="@2xl:col-span-3 @2xl:row-start-3 @2xl:mx-auto @2xl:w-1/2">{walls.south}</div>
      </div>
    </div>
  );
}
