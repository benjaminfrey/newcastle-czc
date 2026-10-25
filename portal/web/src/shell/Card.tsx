import type { FormEvent, ReactNode } from "react";
import { commitFocused } from "./commitFocused";
import ProgressBar from "./ProgressBar";

// The card (task-list brief §4.3, and the comp in specs/assets/): the row colour, a 0.5 px
// hairline edge, 12 px corners, no shadow; header, body and footer bands. Only the body slides.
// With onSubmit, the card is a form, so Return in a field means Continue.
function Card({ wide, onSubmit, children }: { wide?: boolean; onSubmit?: () => void; children: ReactNode }) {
  const cls = `mx-auto flex w-full ${wide ? "max-w-[760px]" : "max-w-[640px]"} flex-col overflow-hidden rounded-[12px] border-[0.5px] border-[var(--app-separator)] bg-[var(--app-row)]`;
  if (!onSubmit) return <section className={cls}>{children}</section>;
  const submit = (e: FormEvent) => { e.preventDefault(); commitFocused(); onSubmit(); };
  return <form noValidate onSubmit={submit} className={cls}>{children}</form>;
}

// The task's name (or "Building 1 · A home"), the bar and "3 of 6"; or a title and a note.
function Header({ title, count, at = 0, aside }: { title: ReactNode; count?: number; at?: number; aside?: ReactNode }) {
  return (
    <div data-card-header className="flex items-center gap-[10px] border-b-[0.5px] border-[var(--app-separator)] px-4 py-[10px] text-[13px] text-[var(--app-secondary-label)]">
      <span className="min-w-0 truncate">{title}</span>
      {count !== undefined && count > 0 ? (
        <>
          <ProgressBar count={count} at={at} />
          <span className="shrink-0 tabular-nums">{at + 1} of {count}</span>
        </>
      ) : aside !== undefined && <span className="ml-auto shrink-0">{aside}</span>}
    </div>
  );
}

const reduced = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

// The question and its control, centred; the next card's body slides in from the right, Back's
// from the left, 300 ms (index.css); a short fade with reduced motion.
function Body({ motionKey, direction = 1, children, className }: {
  motionKey?: string; direction?: 1 | -1; children: ReactNode; className?: string;
}) {
  const motion = motionKey === undefined ? "" : reduced() ? "pane-fade" : direction < 0 ? "pane-pull" : "pane-push";
  return (
    // On a phone the card fills the screen, so a long body scrolls between the header and footer.
    <div key={motionKey} data-card-body data-pane className={`flex min-h-0 flex-1 flex-col items-center overflow-y-auto px-6 pb-[18px] pt-[22px] text-center ${motion} ${className ?? ""}`}>
      {children}
    </div>
  );
}

// A card's rows that may run long (a check page, the buildings list): on a phone they scroll between
// the header and the footer, which stays the card's bottom band.
function Scroll({ children }: { children: ReactNode }) {
  return <div data-card-scroll className="min-h-0 flex-1 overflow-y-auto">{children}</div>;
}

type Press = { label: ReactNode; onPress: () => void; aria?: string; plain?: boolean };

// Back on the left; Continue on the right (filled), or a quiet hint where a tap moves on.
function Footer({ back, next, extra }: { back?: Press; next?: Press | { hint: string } | null; extra?: ReactNode }) {
  return (
    <div data-card-footer className="flex flex-wrap items-center gap-[10px] border-t-[0.5px] border-[var(--app-separator)] px-4 py-[10px]">
      {back && <button type="button" className="btn" aria-label={back.aria} onClick={() => { commitFocused(); back.onPress(); }}>{back.label}</button>}
      {extra}
      {next && "hint" in next && <span className="ml-auto text-[13px] text-[var(--app-secondary-label)]">{next.hint}</span>}
      {next && "onPress" in next && (
        // Continue is the card's one filled button; a skip is plain.
        <button type="button" data-filled={next.plain ? undefined : ""} className={`btn ml-auto ${next.plain ? "" : "btn-filled"}`} aria-label={next.aria}
                onClick={() => { commitFocused(); next.onPress(); }}>{next.label}</button>
      )}
    </div>
  );
}

Card.Header = Header;
Card.Body = Body;
Card.Footer = Footer;
Card.Scroll = Scroll;
export default Card;
