import { Description, Input, Label, TextField } from "@heroui/react";
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { getMe, putMe, signOut, UNREACHABLE, type Me } from "../api";
import AppShell from "../shell/AppShell";

type Key = "name" | "phone" | "mailing_address";
const LABELS: Record<Key, string> = { name: "Full name", phone: "Phone", mailing_address: "Mailing address" };
const WORD: Record<Key, string> = { name: "name", phone: "phone", mailing_address: "mailing address" };

// You (projects brief §3.6): the account's details, each with Change (saved once, for every
// application); the email is the account, so it isn't changed here; and Sign out.
export default function You() {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [editing, setEditing] = useState<Key | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getMe().then((m) => m && m !== "unavailable" && setMe(m)); }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!me || !editing) return;
    const next = { name: me.name ?? null, phone: me.phone ?? null, mailing_address: me.mailing_address ?? null, [editing]: draft.trim() || null };
    const r = await putMe(next);
    if (typeof r === "string") return setError(r === "invalid" ? "That's too long. Please shorten it." : UNREACHABLE);
    setMe(r);
    setEditing(null);
    setError(null);
  }
  async function leave() {
    await signOut();
    navigate("/", { replace: true });
  }

  const box = "overflow-hidden rounded-[12px] border-[0.5px] border-[var(--app-separator)] bg-[var(--app-row)]";
  const row = "flex min-h-12 items-center gap-3 px-4 py-[11px] text-[14px]";
  return (
    <AppShell title="You">
      <div className="mx-auto flex max-w-lg flex-col gap-6 px-4 py-6">
        <h2 className="text-[30px] font-bold leading-tight">You</h2>
        {me && (
          <ul className={box}>
            {(Object.keys(LABELS) as Key[]).map((k, i) => (
              <li key={k} className={i ? "border-t-[0.5px] border-[var(--app-separator)]" : ""}>
                {editing === k ? (
                  <form onSubmit={save} className="flex flex-col gap-2 px-4 py-3">
                    <TextField value={draft} onChange={setDraft} autoComplete={{ name: "name", phone: "tel", mailing_address: "street-address" }[k]}>
                      <Label>{LABELS[k]}</Label>
                      <Input className="min-h-11" autoFocus />
                      {k === "mailing_address" && <Description>Street or PO box, town, state and ZIP code.</Description>}
                    </TextField>
                    {error && <p role="alert" className="text-[15px] text-[var(--app-destructive)]">{error}</p>}
                    <div className="flex gap-2">
                      <button type="submit" data-filled="" className="btn btn-filled">Save</button>
                      <button type="button" className="btn" onClick={() => { setEditing(null); setError(null); }}>Cancel</button>
                    </div>
                  </form>
                ) : (
                  <div className={row}>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[12px] text-[var(--app-secondary-label)]">{LABELS[k]}</span>
                      <span className="block text-[var(--app-label)]">{me[k] || "Not given yet"}</span>
                    </span>
                    <button type="button" aria-label={`Change ${WORD[k]}`} className="min-h-11 px-1 text-[13px] text-[var(--app-accent-text)]"
                            onClick={() => { setEditing(k); setDraft(me[k] ?? ""); }}>Change</button>
                  </div>
                )}
              </li>
            ))}
            <li className={`${row} border-t-[0.5px] border-[var(--app-separator)]`}>
              <span className="min-w-0 flex-1">
                <span className="block text-[12px] text-[var(--app-secondary-label)]">Email — the address you sign in with</span>
                <span className="block text-[var(--app-label)]">{me.email}</span>
              </span>
            </li>
          </ul>
        )}
        <button type="button" className="btn w-full" onClick={() => void leave()}>Sign out</button>
      </div>
    </AppShell>
  );
}
