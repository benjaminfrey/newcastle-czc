export type Me = { email: string; role: string };
export type LinkResult = "sent" | "too_many_requests" | "email_unavailable" | "invalid_email" | "unreachable";
// "invalid": the link itself is no good. "unavailable": the server or the connection
// failed, so the link may still work and must not be thrown away.
export type VerifyResult = Me | "invalid" | "unavailable";

const json = { "Content-Type": "application/json" };

// fetch rejects only when the request never completed (no signal, server gone).
async function attempt(input: string, init?: RequestInit): Promise<Response | null> {
  try {
    return await fetch(input, init);
  } catch {
    return null;
  }
}

export async function requestLink(email: string): Promise<LinkResult> {
  const r = await attempt("/api/auth/request-link", { method: "POST", headers: json, body: JSON.stringify({ email }) });
  if (!r) return "unreachable";
  if (r.status === 202) return "sent";
  if (r.status === 429) return "too_many_requests";
  if (r.status === 422) return "invalid_email";
  return "email_unavailable";
}

export async function verifyToken(token: string): Promise<VerifyResult> {
  const r = await attempt("/api/auth/verify", { method: "POST", headers: json, body: JSON.stringify({ token }) });
  if (!r || r.status >= 500) return "unavailable";
  if (!r.ok) return "invalid";
  return (await r.json()) as Me;
}

export async function getMe(): Promise<Me | null | "unavailable"> {
  const r = await attempt("/api/me");
  if (!r || r.status >= 500) return "unavailable";
  return r.ok ? ((await r.json()) as Me) : null;
}

export async function signOut(): Promise<void> {
  await attempt("/api/auth/sign-out", { method: "POST" });
}

export const UNREACHABLE = "We couldn't reach the Town's server. Please check your connection and try again.";

// ---- Property lookup (public; no sign-in) ----

export type District = { code: string; name: string | null; in_ruleset: boolean; share: number };
export type Street = { name: string; type: string | null; type_name: string | null; ownership: string | null; frontage_ft: number };
export type Facts = {
  parcel_id: number;
  map_lot: string;
  location: string | null;
  acres: number;
  districts: District[];
  streets: Street[];
  on_state_highway: boolean;
  as_of: { parcels: string; parcels_source: string; districts_source: string | null };
  geometry: { type: "MultiPolygon"; coordinates: number[][][][] };
};
export type Hit = { label: string; lon: number; lat: number; parcel_id: number | null };

export async function searchProperty(q: string): Promise<Hit[] | "unavailable"> {
  const r = await attempt(`/api/property/search?q=${encodeURIComponent(q)}`);
  if (!r || r.status === 503 || r.status >= 500) return "unavailable";
  return r.ok ? ((await r.json()) as Hit[]) : [];
}

export async function parcelAt(lon: number, lat: number): Promise<number | null | "unavailable"> {
  const r = await attempt(`/api/property/at?lon=${lon}&lat=${lat}`);
  if (!r || r.status >= 500) return "unavailable";
  return r.ok ? ((await r.json()) as { parcel_id: number }).parcel_id : null;
}

export async function getProperty(id: number): Promise<Facts | null | "unavailable"> {
  const r = await attempt(`/api/property/${id}`);
  if (!r || r.status >= 500) return "unavailable";
  return r.ok ? ((await r.json()) as Facts) : null;
}

export async function getDistricts(): Promise<{ code: string; name: string }[]> {
  const r = await attempt("/api/property/districts");
  return r && r.ok ? ((await r.json()) as { code: string; name: string }[]) : [];
}
