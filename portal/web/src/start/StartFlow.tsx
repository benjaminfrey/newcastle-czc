import { Link, Navigate, Outlet, useLocation } from "react-router";
import { START_STEPS } from "../forms/steps";
import SignInForm from "../components/SignInForm";
import Card from "../shell/Card";
import { useWideLayout } from "../shell/useWideLayout";

// /start/use is part of "Your project" (choosing the use comes after the property is known).
const STEP_OF: Record<string, string> = { "/start": "project", "/start/use": "project", "/start/property": "property",
                                          "/start/needs": "needs", "/start/signin": "needs" };

// "Do I need a permit?" in the card (task-list brief §9): Home above; the card centred on a
// desktop, filling a phone's screen. "Your project" draws its own card (its bar and footer); the
// property, the use, the result and sign-in sit in a card headed by their step. Signed out.
export default function StartFlow() {
  const wide = useWideLayout();
  const { pathname } = useLocation();
  const path = pathname.replace(/\/$/, "");
  const current = STEP_OF[path] ?? "project";
  const title = START_STEPS.find((s) => s.id === current)!.title;
  const own = path === "/start"; // Your project brings its own card
  const content = own ? <Outlet /> : (
    <Card>
      <Card.Header title={path === "/start/signin" ? "Sign in" : title} />
      <Card.Body motionKey={path} className={path === "/start/needs" || path === "/start/use" ? "items-stretch text-left" : undefined}>
        <Outlet />
      </Card.Body>
    </Card>
  );
  const bar = "flex h-11 items-center border-b-[0.5px] border-[var(--app-separator)] bg-[var(--app-grouped-ground)]/95 px-2 backdrop-blur";
  const home = (
    <Link to="/" aria-label="Home" className="flex min-h-11 items-center gap-1 px-2 text-[17px] text-[var(--app-accent-text)]">
      <span aria-hidden="true" className="text-[22px] leading-none">‹</span>Home
    </Link>
  );
  if (wide) {
    return (
      <div className="min-h-dvh bg-[var(--app-grouped-ground)]">
        <div className={`${bar} sticky top-0 z-10 gap-3 px-6`}>
          {home}<span className="text-[15px] font-medium">Do I need a permit?</span>
        </div>
        <h1 className="sr-only">Do I need a permit?</h1>
        <main className="px-8 pb-8 pt-8">{content}</main>
      </div>
    );
  }
  return (
    <div className="flex h-dvh flex-col bg-[var(--app-grouped-ground)]">
      <div className={`${bar} sticky top-0 z-10`}>{home}</div>
      <h1 className="sr-only">Do I need a permit?</h1>
      <main className="flex min-h-0 flex-1 flex-col px-3 pt-3 [&>*]:min-h-0 [&>*]:flex-1"
            style={{ paddingBottom: "max(12px, env(safe-area-inset-bottom))" }}>
        {content}
      </main>
    </div>
  );
}

// Signing in to start an application: a card of its own after "What you'll need", not a sheet.
// The emailed link comes back to the application's first question.
export function StartSignIn() {
  return (
    <section className="flex w-full flex-col items-center gap-3">
      <h2 tabIndex={-1} data-screen-title className="text-[20px] font-medium leading-[1.3] outline-none">Sign in to apply</h2>
      <p className="max-w-[46ch] text-[13px] text-[var(--app-secondary-label)]">No password. We'll email you a link, and your answers will be waiting.</p>
      <div className="w-full max-w-md text-left"><SignInForm /></div>
    </section>
  );
}

// Addresses from before the redesign.
export function Moved({ to }: { to: string }) {
  const { search } = useLocation();
  return <Navigate to={`${to}${search}`} replace />;
}
