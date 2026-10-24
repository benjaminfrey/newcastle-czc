import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getMe } from "../api";

// One screen, one action: find out what you need. Signed in, a way back to your applications.
export default function Home() {
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => {
    getMe().then((m) => setSignedIn(!!m && m !== "unavailable"));
  }, []);
  return (
    <div className="flex flex-col items-center gap-6 py-10 text-center">
      <img src="/town-seal.png" alt="Town of Newcastle seal" className="size-24" width={96} height={96} />
      <div className="flex flex-col gap-2">
        <h1 className="text-[34px] font-bold leading-tight">Planning a project in Newcastle?</h1>
        <p className="mx-auto max-w-md text-[17px] text-[var(--app-secondary-label)]">
          Answer a few questions to find out which permit you need, then apply here, in about ten steps.
        </p>
      </div>
      <Link to="/start"
            className="flex min-h-12 items-center rounded-full bg-[var(--app-accent)] px-8 text-[17px] font-semibold text-[var(--app-on-accent)]">
        Find out what you need
      </Link>
      {signedIn && (
        <Link to="/my-applications" className="flex min-h-11 items-center text-[17px] text-[var(--app-accent-text)]">
          Continue an application
        </Link>
      )}
    </div>
  );
}
