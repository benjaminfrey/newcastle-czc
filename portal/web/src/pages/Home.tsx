import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { getMe, UNREACHABLE } from "../api";
import SignInForm from "../components/SignInForm";
import Icon from "../controls/Icon";
import { longDate, mapLotLabel } from "../format";
import { listProjects, type ProjectSummary, type Status } from "../projects";
import AppShell from "../shell/AppShell";
import Pill, { type Tone } from "../shell/Pill";

// The pill words for a project's status (projects brief §5.2).
export const STATUS_WORDS: Record<Status, string> = { draft: "Draft", submitted: "Sent", locked: "With the Town", decided: "Decided" };
export const STATUS_TONE: Record<Status, Tone> = { draft: "todo", submitted: "progress", locked: "progress", decided: "done" };
// A part's tile icon, for a project's row: its first part's.
const PART_ICONS: Record<string, string> = {
  building: "building-cottage", addition: "home-plus", renovation: "paint", site: "shovel", use: "building-store",
  driveway: "road", divide: "layout-grid", other: "help-circle",
};

function Seal() {
  return (
    <div className="flex flex-col items-center gap-3 text-center">
      <img src="/town-seal.png" alt="Town of Newcastle seal" className="size-20" width={80} height={80} />
      <h1 className="text-[22px] font-semibold leading-tight">Town of Newcastle — Permits</h1>
    </div>
  );
}

// Signed out (projects brief §3.1): the seal and the sign-in card, nothing else.
export function SignedOut() {
  return (
    <div className="min-h-dvh bg-[var(--app-grouped-ground)] px-4 py-10">
      <div className="mx-auto flex max-w-md flex-col gap-6">
        <Seal />
        <SignInForm hint="No password. We'll email you a link." />
      </div>
    </div>
  );
}

function Row({ p }: { p: ProjectSummary }) {
  const where = mapLotLabel(p.map_lot);
  const how = p.status === "draft"
    ? (p.left ? `${p.left} ${p.left === 1 ? "thing" : "things"} left` : "ready to send")
    : p.submitted_at ? `sent ${longDate(p.submitted_at).replace(/, \d{4}$/, "")}` : "";
  return (
    <Link to={`/projects/${p.id}`} className="flex min-h-14 items-center gap-3 px-4 py-[11px] text-[14px] no-underline">
      <Icon name={PART_ICONS[p.first_part ?? ""] ?? "clipboard-list"} className="text-[var(--app-secondary-label)]" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] font-medium text-[var(--app-label)]">{p.title}</span>
        <span className="block text-[13px] text-[var(--app-secondary-label)]">{where}{how && ` · ${how}`}</span>
      </span>
      <Pill tone={STATUS_TONE[p.status]}>{STATUS_WORDS[p.status]}</Pill>
      <Icon name="chevron-right" className="text-[var(--app-tertiary-label)]" />
    </Link>
  );
}

// Signed in (projects brief §3.2): every project, newest change first, under the page's title,
// with Start a new application and Continue an application beside it. The seal is the shell's.
function SignedIn() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<ProjectSummary[] | null>(null);
  const [note, setNote] = useState<string | null>(null);
  useEffect(() => {
    listProjects().then((r) => (typeof r === "string" ? setNote(UNREACHABLE) : setRows(r)));
  }, []);
  function carryOn() {
    const open = (rows ?? []).find((p) => p.status === "draft" || p.status === "submitted");
    if (open) navigate(`/projects/${open.id}`);
    else setNote("You have no application in progress.");
  }
  return (
    <AppShell title="Home" titled>
    <div className="mx-auto flex w-full max-w-[1040px] flex-col gap-6">
      <header className="flex flex-col gap-4">
        <h1 className="text-[30px] font-bold leading-tight">Your applications</h1>
        <div className="flex flex-wrap gap-3">
          <Link to="/new" data-filled="" className="btn btn-filled no-underline">Start a new application</Link>
          <button type="button" className="btn" onClick={carryOn}>Continue an application</button>
        </div>
        {note && <p role="status" className="text-[15px] text-[var(--app-secondary-label)]">{note}</p>}
      </header>
      {rows && rows.length === 0 && (
        <p className="text-[15px] text-[var(--app-secondary-label)]">Nothing yet. Start a new application to apply for a permit.</p>
      )}
      {rows && rows.length > 0 && (
        <section className="flex max-w-[720px] flex-col gap-2">
          <ul aria-label="Your applications"
              className="overflow-hidden rounded-[12px] border-[0.5px] border-[var(--app-separator)] bg-[var(--app-row)]">
            {rows.map((p, i) => (
              <li key={p.id} className={i ? "border-t-[0.5px] border-[var(--app-separator)]" : ""}><Row p={p} /></li>
            ))}
          </ul>
        </section>
      )}
    </div>
    </AppShell>
  );
}

export default function Home() {
  const [state, setState] = useState<"checking" | "in" | "out">("checking");
  useEffect(() => {
    getMe().then((m) => setState(m && m !== "unavailable" ? "in" : "out"));
  }, []);
  if (state === "checking") return null;
  return state === "in" ? <SignedIn /> : <SignedOut />;
}
