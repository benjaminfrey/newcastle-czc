// The applicant's answers to "Do I need a permit?", kept in this browser tab
// (like the chosen property) until an application is started in M4.

export type ProjectKind = "build" | "use" | "driveway" | "divide" | "other";
export type ScreenerAnswers = {
  project: ProjectKind[];
  use_key: string | null;
  building: {
    kind: "new" | "addition" | "renovation" | "site" | null;
    gross_floor_area_sf: number | null; // being built or added
    total_floor_area_sf: number | null; // the whole building, for renovations
    parking_spaces: number | null;
    new_dwelling_units: number | null; // homes being built or placed, not ones already there
  };
  division: { lots_after: number | null };
};

const KEY = "portal.screener";

export function saveAnswers(a: ScreenerAnswers): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(a));
  } catch {
    // Blocked storage: the flow still works within the page; nothing is kept.
  }
}

export function loadAnswers(): ScreenerAnswers | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as ScreenerAnswers) : null;
  } catch {
    return null;
  }
}

// "8.15.b.1" → "Art. 8 §15.b.1"
export function citeLabel(ref: string): string {
  const [art, ...rest] = ref.split(".");
  return `Art. ${art} §${rest.join(".")}`;
}
