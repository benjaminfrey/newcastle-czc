import { Navigate, Outlet, useLocation } from "react-router";
import { START_STEPS } from "../forms/steps";
import { loadProperty } from "../property";
import { loadAnswers } from "../screener";
import AppShell from "../shell/AppShell";
import type { ShellStep } from "../shell/types";

const PATHS: Record<string, string> = { project: "/start", property: "/start/property", needs: "/start/needs" };
// /start/use is part of "Your project" (choosing the use comes after the property is known).
const STEP_OF: Record<string, string> = { "/start": "project", "/start/use": "project", "/start/property": "property", "/start/needs": "needs" };

// "Do I need a permit?" in the application window: Your project, Your property, What you'll need.
// Signed out; each pane brings its own form and Continue.
export default function StartFlow() {
  const { pathname } = useLocation();
  const current = STEP_OF[pathname.replace(/\/$/, "")] ?? "project";
  const answered = { project: !!loadAnswers(), property: !!loadProperty(), needs: false } as Record<string, boolean>;
  const steps: ShellStep[] = START_STEPS.map((s) => ({
    id: s.id, title: s.title, href: PATHS[s.id], unknowns: 0,
    status: answered[s.id] && s.id !== current ? "done" : answered[s.id] ? "done" : "todo",
  }));
  return (
    <AppShell steps={steps} currentId={current} formTitle="Do I need a permit?" saveState="idle" rootHref="/" backLabel="Home">
      <Outlet />
    </AppShell>
  );
}

// Addresses from before the redesign.
export function Moved({ to }: { to: string }) {
  const { search } = useLocation();
  return <Navigate to={`${to}${search}`} replace />;
}
