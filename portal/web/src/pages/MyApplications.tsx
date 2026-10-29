import { Button } from "@heroui/react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { getMe, signOut, UNREACHABLE, type Me } from "../api";
import { listApplications, type AppSummary } from "../applications";
import InsetGroup from "../shell/InsetGroup";
import { longDate, mapLotLabel } from "../format";

export default function MyApplications() {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [list, setList] = useState<AppSummary[] | null>(null);

  useEffect(() => {
    getMe().then((m) => {
      if (m === "unavailable") setUnreachable(true);
      else if (m) {
        setMe(m);
        listApplications().then((l) => (typeof l === "string" ? setUnreachable(true) : setList(l)));
      } else navigate("/signin", { replace: true });
    });
  }, [navigate]);

  if (unreachable) return <p role="alert">{UNREACHABLE}</p>;
  if (!me) return <p>Loading…</p>;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[30px] font-bold leading-tight">My applications</h1>
          <p className="text-[15px] text-[var(--app-secondary-label)]">Signed in as {me.email}</p>
        </div>
        <Button variant="ghost" className="min-h-11 text-[17px] text-[var(--app-accent-text)]"
                onPress={() => signOut().then(() => navigate("/", { replace: true }))}>
          Sign out
        </Button>
      </div>
      {list === null && <p className="text-[var(--app-secondary-label)]">Loading…</p>}
      {list?.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-10 text-center">
          <p className="text-[17px] text-[var(--app-secondary-label)]">You haven't started any applications yet.</p>
          <Link to="/start"
                className="flex min-h-12 items-center rounded-xl bg-[var(--app-accent)] px-8 text-[17px] font-semibold text-[var(--app-on-accent)] no-underline">
            Start an application
          </Link>
        </div>
      )}
      {list && list.length > 0 && (
        <InsetGroup>
          {list.map((a) => (
            <Link key={a.id} to={`/applications/${a.id}`}
                  className="flex min-h-14 items-center gap-3 px-4 py-2 no-underline">
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="text-[17px]">{a.official_title}</span>
                <span className="text-[15px] text-[var(--app-secondary-label)]">
                  {mapLotLabel(a.map_lot)} · Not sent yet · Last changed {longDate(a.updated_at)}
                </span>
              </span>
              <span aria-hidden="true" className="text-[var(--app-tertiary-label)]">›</span>
            </Link>
          ))}
        </InsetGroup>
      )}
    </div>
  );
}
