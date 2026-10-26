import { useEffect, useState } from "react";
import { Outlet } from "react-router";
import { getMe, UNREACHABLE } from "../api";
import { SignedOut } from "../pages/Home";

// Sign in first (projects brief §1): every page but Home and the emailed link shows the sign-in
// card to a visitor who isn't signed in.
export default function RequireSignIn() {
  const [state, setState] = useState<"checking" | "in" | "out" | "unavailable">("checking");
  useEffect(() => {
    getMe().then((m) => setState(m === "unavailable" ? "unavailable" : m ? "in" : "out"));
  }, []);
  if (state === "checking") return null;
  if (state === "unavailable") return <p role="alert" className="p-8">{UNREACHABLE}</p>;
  return state === "in" ? <Outlet /> : <SignedOut />;
}
