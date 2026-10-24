import { Button, Modal } from "@heroui/react";
import { createContext, type ReactNode } from "react";
import { useWideLayout } from "./useWideLayout";

// Rows inside a sheet always stack their label over the control: a sheet is narrow even on a desktop.
export const InSheet = createContext(false);

type Props = {
  // No onDone: a sheet that only closes (sign-in) shows Cancel alone. No onCancel: a sheet whose
  // answers save as they're given (a building, an edit on review) shows Done alone, as on iOS —
  // a Cancel there couldn't undo anything.
  open: boolean; title: string; onCancel?: () => void; onDone?: () => void;
  pages?: string[]; pageIndex?: number; onPage?: (i: number) => void; doneLabel?: string;
  children: ReactNode;
};

// A sheet: over the window on desktop, full height on a phone. Cancel on the left, Done on the
// right, page dots when the item has pages. Esc cancels.
export default function Sheet({ open, title, onCancel, onDone, pages, pageIndex = 0, onPage, doneLabel = "Done", children }: Props) {
  const wide = useWideLayout();
  return (
    <Modal.Backdrop isOpen={open} onOpenChange={(o) => !o && (onCancel ?? onDone)?.()} isDismissable={false}>
      <Modal.Container size={wide ? "lg" : "full"} scroll="inside">
        <Modal.Dialog className="app-sheet bg-[var(--app-ground)] p-0" aria-label={title}>
          <Modal.Header className="grid grid-cols-[1fr_auto_1fr] items-center border-b border-[var(--app-separator)] bg-[var(--app-row)] px-2 py-1.5">
            {onCancel ? <Button variant="ghost" className="min-h-11 justify-self-start" onPress={onCancel}>Cancel</Button> : <span />}
            <Modal.Heading className="text-[17px] font-semibold">{title}</Modal.Heading>
            {onDone ? (
              <Button variant="ghost" className="min-h-11 justify-self-end font-semibold text-[var(--app-accent-text)]" onPress={onDone}>
                {doneLabel}
              </Button>
            ) : <span />}
          </Modal.Header>
          {/* HeroUI's body text is muted; questions in a sheet read like questions anywhere else. */}
          <Modal.Body className="flex flex-col gap-6 overflow-x-hidden px-4 py-5 text-[15px] text-[var(--app-label)]"><InSheet.Provider value>{children}</InSheet.Provider></Modal.Body>
          {pages && pages.length > 1 && (
            // Back and Next stay in view beside the dots, as in Setup Assistant; the body scrolls.
            <Modal.Footer className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 border-t border-[var(--app-separator)] bg-[var(--app-row)] px-3 py-2">
              {pageIndex > 0
                ? <Button variant="secondary" className="min-h-11 justify-self-start" onPress={() => onPage?.(pageIndex - 1)}>Back</Button>
                : <span />}
              <div className="flex flex-col items-center">
                <p aria-hidden="true" className="text-[13px] text-[var(--app-secondary-label)]">{pageIndex + 1} of {pages.length}</p>
                <div role="tablist" aria-label="Pages" className="flex">
                  {pages.map((p, i) => (
                    <button key={p} type="button" role="tab" aria-label={p} aria-selected={i === pageIndex}
                            onClick={() => onPage?.(i)} className="flex size-8 items-center justify-center">
                      <span className={`size-2 rounded-full ${i === pageIndex ? "bg-[var(--app-label)]" : "bg-[var(--app-tertiary-label)]"}`} />
                    </button>
                  ))}
                </div>
              </div>
              {pageIndex < pages.length - 1
                ? <Button variant="primary" className="min-h-11 justify-self-end" onPress={() => onPage?.(pageIndex + 1)}>Next: {pages[pageIndex + 1]}</Button>
                : <span />}
            </Modal.Footer>
          )}
        </Modal.Dialog>
      </Modal.Container>
    </Modal.Backdrop>
  );
}
