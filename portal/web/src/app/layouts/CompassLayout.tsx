import type { ReactNode } from "react";

// The four walls' window shares around a small plan of the building, so "north" is a place on
// a picture rather than a word to work out. The street side is named when the map knows it.
export default function CompassLayout({ walls, street }: { walls: Record<"north" | "east" | "south" | "west", ReactNode>; street?: string | null }) {
  return (
    <div className="flex flex-col gap-3">
      {street && <p className="text-center text-[15px] text-[var(--app-secondary-label)]">The front faces {street}</p>}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_7rem_1fr] sm:grid-rows-[auto_7rem_auto] sm:items-center">
        <div className="sm:col-span-3 sm:row-start-1 sm:mx-auto sm:w-1/2">{walls.north}</div>
        <div className="sm:col-start-1 sm:row-start-2">{walls.west}</div>
        <div aria-hidden="true" className="hidden sm:col-start-2 sm:row-start-2 sm:flex sm:size-28 sm:items-center sm:justify-center sm:rounded-lg sm:border-2 sm:border-[var(--app-label)]">
          <span className="text-[13px] font-semibold">N ↑</span>
        </div>
        <div className="sm:col-start-3 sm:row-start-2">{walls.east}</div>
        <div className="sm:col-span-3 sm:row-start-3 sm:mx-auto sm:w-1/2">{walls.south}</div>
      </div>
    </div>
  );
}
