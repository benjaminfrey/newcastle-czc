import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getMe } from "../api";
import InsetGroup from "../shell/InsetGroup";

// One screen, one action: find out what you need. Signed in, a way back to your applications.
export default function Home() {
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => {
    getMe().then((m) => setSignedIn(!!m && m !== "unavailable"));
  }, []);
  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6 py-6">
      <div className="flex flex-col items-center gap-4 text-center">
        <img src="/town-seal.png" alt="Town of Newcastle seal" className="size-20" width={80} height={80} />
        <div className="flex flex-col gap-2">
          <h1 className="text-[30px] font-bold leading-tight">Planning a project in Newcastle?</h1>
          <p className="text-[17px] text-[var(--app-secondary-label)]">
            Answer a few questions to find out which permit you need, then apply here, in about ten steps.
          </p>
        </div>
        <Link to="/start"
              className="flex min-h-12 w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-8 text-[17px] font-semibold text-[var(--app-on-accent)] no-underline">
          Find out what you need
        </Link>
      </div>
      {signedIn && (
        <InsetGroup>
          <Link to="/my-applications" className="flex min-h-12 items-center gap-3 px-4 text-[17px] no-underline">
            <span className="flex-1">Continue an application</span>
            <span aria-hidden="true" className="text-[var(--app-tertiary-label)]">›</span>
          </Link>
        </InsetGroup>
      )}
    </div>
  );
}
