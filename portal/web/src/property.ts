// The property the applicant chose on the "Where is it?" page. Kept in this
// browser tab until M4 saves it with an application.

export type ChosenProperty = {
  source: "lookup" | "manual";
  parcel_id: number | null;
  map_lot: string;
  district_code: string | null;
  disputed: boolean;
  note: string;
  as_of: string | null;
};

const KEY = "portal.property";

export function saveProperty(p: ChosenProperty): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(p));
  } catch {
    // Private windows and blocked storage: the page still works; nothing is kept.
  }
}

export function loadProperty(): ChosenProperty | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as ChosenProperty) : null;
  } catch {
    return null;
  }
}
