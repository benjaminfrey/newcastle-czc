import { Description, Input, Label, TextField } from "@heroui/react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { getMe, putMe, UNREACHABLE, type Facts, type Me } from "../api";
import Icon from "../controls/Icon";
import { MultiTiles } from "../controls/Tiles";
import Where from "../pages/Where";
import { createProject, getParts, type FormField, type PartDef, type PropertyChoice } from "../projects";
import type { ChosenProperty } from "../property";
import Card from "../shell/Card";

// The parts joined by "and", lower-cased after the first, plus the street: "A new building and a
// driveway at Sheepscot Road" (projects brief §3.3). The title can be renamed on the dashboard.
export function defaultTitle(labels: string[], location: string | null): string {
  const words = labels.map((l, i) => (i === 0 ? l : l[0].toLowerCase() + l.slice(1)));
  const joined = words.length < 2 ? words.join("") : `${words.slice(0, -1).join(", ")} and ${words.at(-1)}`;
  const street = location ? location.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()) : null;
  return street ? `${joined} at ${street}` : joined;
}

const filled = (m: Me | null) => !!(m?.name && m.phone && m.mailing_address);
const ASK: Record<number, [string, string | null]> = {
  0: ["How can the Town reach you?", "Saved on your account, for every application."],
  1: ["Where is the work?", null],
  2: ["What are you doing here?", "Choose all that apply. You can add more later."],
};

// Starting a project: three cards (projects brief §3.3) — how to reach you (skipped once the
// account has it), where the work is, and its parts. "Go to my project" creates it and opens the
// dashboard.
export default function NewProject() {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [at, setAt] = useState<number | null>(null);
  const [dir, setDir] = useState<1 | -1>(1);
  const [details, setDetails] = useState({ name: "", phone: "", mailing_address: "" });
  const [place, setPlace] = useState<{ p: ChosenProperty; facts: Facts | null } | null>(null);
  const [parts, setParts] = useState<PartDef[]>([]);
  const [chosen, setChosen] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getMe().then((m) => {
      const mine = m && m !== "unavailable" ? m : null;
      setMe(mine);
      setDetails({ name: mine?.name ?? "", phone: mine?.phone ?? "", mailing_address: mine?.mailing_address ?? "" });
      setAt(filled(mine) ? 1 : 0);
    });
    getParts().then((p) => typeof p !== "string" && setParts(p));
  }, []);
  const skipFirst = filled(me);
  useEffect(() => { document.querySelector<HTMLElement>("[data-screen-title]")?.focus(); }, [at]);
  if (at === null) return null;

  const go = (n: number) => { setDir(n > at ? 1 : -1); setError(null); setAt(n); };

  async function saveDetails() {
    const blank = [!details.name.trim() && "a full name", !details.phone.trim() && "a phone number",
                   !details.mailing_address.trim() && "a mailing address"].filter(Boolean) as string[];
    if (blank.length) {
      return setError(`Please give ${blank.length > 1 ? `${blank.slice(0, -1).join(", ")} and ${blank.at(-1)}` : blank[0]}.`);
    }
    setBusy(true);
    const r = await putMe({ name: details.name.trim(), phone: details.phone.trim(), mailing_address: details.mailing_address.trim() });
    setBusy(false);
    if (typeof r === "string") return setError(r === "invalid" ? "One of those is too long. Please shorten it." : UNREACHABLE);
    go(1);
  }

  async function start() {
    if (!chosen.length) return setError("Choose at least one.");
    if (!place) return go(1);
    const property: PropertyChoice = place.p.source === "lookup" && place.p.parcel_id !== null
      ? { source: "lookup", parcel_id: place.p.parcel_id }
      : { source: "manual", map_lot: place.p.map_lot, district_code: place.p.district_code };
    const labels = parts.filter((x) => chosen.includes(x.id)).map((x) => x.label);
    setBusy(true);
    const r = await createProject({ property, disputed: place.p.disputed, note: place.p.note, parts: chosen,
                                     title: defaultTitle(labels, place.facts?.location ?? null) });
    setBusy(false);
    if (typeof r === "string") {
      return setError(r === "busy" ? "The Town's server is busy. Please wait a minute and try again."
        : r === "not_approved" ? "Applications aren't open yet. Please contact the Town Office." : UNREACHABLE);
    }
    navigate(`/projects/${r.id}`);
  }

  const [question, help] = ASK[at];
  const field = { id: "parts", label: question, official_label: question, type: "multichoice",
    options: parts.map((x) => ({ value: x.id, label: x.label, official: x.label, icon: x.icon })) } as unknown as FormField;
  const body = at === 0 ? (
    <div className="flex w-full max-w-md flex-col gap-4 text-left">
      {(["name", "phone", "mailing_address"] as const).map((k) => (
        <TextField key={k} value={details[k]} onChange={(v) => setDetails((d) => ({ ...d, [k]: v }))}
                   autoComplete={{ name: "name", phone: "tel", mailing_address: "street-address" }[k]}>
          <Label>{{ name: "Full name", phone: "Phone", mailing_address: "Mailing address" }[k]}</Label>
          <Input className="min-h-11" />
          {k === "mailing_address" && <Description>Street or PO box, town, state and ZIP code.</Description>}
        </TextField>
      ))}
      <p className="text-[13px] text-[var(--app-secondary-label)]">
        Email <span className="text-[var(--app-label)]">{me?.email}</span> — the address you signed in with.
      </p>
    </div>
  ) : at === 1 ? (
    <Where onDone={(p, facts) => { setPlace({ p, facts }); go(2); }} />
  ) : (
    <MultiTiles field={field} value={chosen} onValue={(v) => { setChosen((v as string[] | null) ?? []); setError(null); }} />
  );
  const count = 3;
  const shown = skipFirst ? at - 1 : at;
  const total = skipFirst ? 2 : 3;
  return (
    <div className="min-h-dvh bg-[var(--app-grouped-ground)] px-3 py-3 lg:px-8 lg:py-8">
      <h1 className="sr-only">Start a new application</h1>
      <Card onSubmit={at === 0 ? () => void saveDetails() : at === 2 ? () => void start() : undefined}>
        <Card.Header title={<span className="inline-flex items-center gap-1.5"><Icon name="clipboard-list" />New application</span>}
                     count={count} at={at} />
        <Card.Body motionKey={String(at)} direction={dir} className={at === 1 ? "items-stretch" : undefined}>
          {at !== 1 && (
            <>
              <h2 tabIndex={-1} data-screen-title className="max-w-[30ch] text-balance text-[20px] font-medium leading-[1.3] outline-none">{question}</h2>
              <p className="mb-4 mt-1 max-w-[46ch] text-pretty text-[13px] text-[var(--app-secondary-label)]">{help ?? ""}</p>
            </>
          )}
          {body}
          {error && <p role="alert" className="mt-3 text-[15px] text-[var(--app-destructive)]">{error}</p>}
        </Card.Body>
        <Card.Footer
          back={at > (skipFirst ? 1 : 0) ? { label: "Back", onPress: () => go(at - 1) } : { label: "Cancel", onPress: () => navigate("/") }}
          next={at === 0 ? { label: busy ? "Saving…" : "Continue", onPress: () => void saveDetails() }
            : at === 2 ? { label: busy ? "Starting…" : "Go to my project", onPress: () => void start() } : null} />
        <p className="sr-only" aria-live="polite">Card {shown + 1} of {total}: {question}</p>
      </Card>
    </div>
  );
}
