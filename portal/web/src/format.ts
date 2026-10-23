const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                "October", "November", "December"];

// "2012-04-01" → "April 1, 2012", without time-zone surprises.
export function longDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

// "004-036" → "Map 4, Lot 36"; "003-073-00B" → "Map 3, Lot 73-B".
export function mapLotLabel(mapLot: string): string {
  const [map, ...lot] = mapLot.split("-");
  if (lot.length === 0) return mapLot;
  return `Map ${Number(map) || map}, Lot ${lot.map((p) => p.replace(/^0+(?=.)/, "")).join("-")}`;
}
