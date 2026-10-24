import { useEffect, useRef, type FormEvent, type PointerEvent, type ReactNode } from "react";
import { commitFocused, isLongText } from "./commitFocused";
import { useNavigate } from "react-router";
import ActionBar from "./ActionBar";
import NavBar from "./NavBar";
import StepList from "./StepList";
import StepSidebar from "./StepSidebar";
import Toolbar from "./Toolbar";
import type { SaveState, ShellActions, ShellStep } from "./types";
import { useWideLayout } from "./useWideLayout";

type Props = {
  steps: ShellStep[];
  currentId: string | null; // null: the phone's root list (on a desktop, the first step's pane)
  formTitle: string;
  saveState: SaveState;
  rootHref: string;
  onDone?: () => void;
  onReload?: () => void;
  onStep?: (id: string) => void; // ⌥⌘↑ / ⌥⌘↓
  actions?: ShellActions;
  backLabel?: string; // the phone's ‹ chevron: "Application", or "Home" for the start steps
  children?: ReactNode;
};

// The application window: on a desktop, a sidebar of steps beside the content pane (toolbar,
// content, Back and Continue); on a phone, a list of steps that pushes each step in. The
// content sits in one form, so Return anywhere in a field means Continue.
export default function AppShell({ steps, currentId, formTitle, saveState, rootHref, onDone, onReload, onStep, actions = {}, backLabel = "Application", children }: Props) {
  const wide = useWideLayout();
  const navigate = useNavigate();
  const flat = steps.flatMap((s) => [s, ...(s.children ?? [])]);
  const current = flat.find((s) => s.id === currentId);
  const reduced = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  // A step slides in on a phone and cross-fades on a desktop; with reduced motion, a short fade.
  const motion = reduced ? "pane-fade" : wide ? "pane-cross" : "pane-push";
  const top = steps.findIndex((s) => s.id === currentId || s.children?.some((c) => c.id === currentId));

  // The iOS edge swipe: a drag that starts at the left edge and moves right goes back.
  const swipe = useRef<number | null>(null);
  const onPointerDown = (e: PointerEvent) => { swipe.current = !wide && e.clientX <= 20 ? e.clientX : null; };
  const onPointerUp = (e: PointerEvent) => {
    if (swipe.current !== null && e.clientX - swipe.current >= 80) {
      commitFocused();
      navigate(rootHref);
    }
    swipe.current = null;
  };

  useEffect(() => {
    if (!onStep || !currentId) return;
    const onKey = (e: KeyboardEvent) => {
      if (!(e.altKey || e.metaKey) || (e.key !== "ArrowDown" && e.key !== "ArrowUp") || isLongText(e.target)) return;
      const at = steps.findIndex((s) => s.id === currentId);
      const next = steps[at + (e.key === "ArrowDown" ? 1 : -1)];
      if (next) {
        e.preventDefault();
        commitFocused();
        onStep(next.id);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [steps, currentId, onStep]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    commitFocused();
    actions.onContinue?.();
  }

  if (!wide && !current) return <StepList steps={steps} title="Your application" subtitle={formTitle} />;

  // A pane that brings its own form (the start steps) gets a plain container, never a nested form.
  const cls = `flex flex-col gap-6 ${wide ? "px-8 py-6" : "px-4 pb-32 pt-2"}`;
  const inner = actions.onContinue || actions.back ? (
    <form onSubmit={onSubmit} noValidate className={cls}>
      {children}
      <ActionBar actions={actions} wide={wide} />
    </form>
  ) : <div className={cls}>{children}</div>;
  const content = (
    <div key={currentId ?? "root"} data-pane className={motion} onPointerDown={onPointerDown} onPointerUp={onPointerUp}>
      {inner}
      {current && top >= 0 && (
        <p data-testid="step-announcer" aria-live="polite" className="sr-only">
          Step {top + 1} of {steps.length}: {current.title}
        </p>
      )}
    </div>
  );

  if (!wide) {
    return (
      <div className="min-h-dvh bg-[var(--app-ground)]">
        <NavBar title={current!.title} backHref={rootHref} backLabel={backLabel} saveState={saveState} onReload={onReload} />
        {content}
      </div>
    );
  }
  return (
    <div className="grid min-h-dvh grid-cols-[17rem_1fr] bg-[var(--app-ground)]">
      <aside className="border-r border-[var(--app-separator)] bg-[var(--app-grouped-ground)]">
        <StepSidebar steps={steps} currentId={currentId} title={formTitle} />
      </aside>
      <main className="flex min-w-0 flex-col">
        <Toolbar title={current?.title ?? formTitle} saveState={saveState} onDone={onDone} onReload={onReload} />
        <div className="mx-auto w-full max-w-3xl">{content}</div>
      </main>
    </div>
  );
}
