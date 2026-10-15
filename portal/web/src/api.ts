export type Me = { email: string; role: string };
export type LinkResult = "sent" | "too_many_requests" | "email_unavailable" | "invalid_email";

const json = { "Content-Type": "application/json" };

export async function requestLink(email: string): Promise<LinkResult> {
  const r = await fetch("/api/auth/request-link", { method: "POST", headers: json, body: JSON.stringify({ email }) });
  if (r.status === 202) return "sent";
  if (r.status === 429) return "too_many_requests";
  if (r.status === 422) return "invalid_email";
  return "email_unavailable";
}

export async function verifyToken(token: string): Promise<Me | null> {
  const r = await fetch("/api/auth/verify", { method: "POST", headers: json, body: JSON.stringify({ token }) });
  return r.ok ? ((await r.json()) as Me) : null;
}

export async function getMe(): Promise<Me | null> {
  const r = await fetch("/api/me");
  return r.ok ? ((await r.json()) as Me) : null;
}

export async function signOut(): Promise<void> {
  await fetch("/api/auth/sign-out", { method: "POST" });
}
