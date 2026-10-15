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
