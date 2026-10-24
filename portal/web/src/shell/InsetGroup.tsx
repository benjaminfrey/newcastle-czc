import { useId, type ReactNode } from "react";
import { useWideLayout } from "./useWideLayout";

type GroupProps = { title?: string; footer?: ReactNode; children: ReactNode };

// A grouped inset list (System Settings, iOS Settings): rounded white rows on the grouped ground,
// hairline separators, an optional small heading above and footnote below.
function InsetGroup({ title, footer, children }: GroupProps) {
  const id = useId();
  return (
    <section role="group" aria-labelledby={title ? id : undefined} className="flex flex-col gap-1.5">
      {title && <h2 id={id} className="px-4 text-[13px] font-semibold uppercase tracking-wide text-[var(--app-secondary-label)]">{title}</h2>}
      <div className="divide-y divide-[var(--app-separator)] overflow-hidden rounded-xl bg-[var(--app-row)]">{children}</div>
      {footer && <p className="px-4 text-[13px] text-[var(--app-secondary-label)]">{footer}</p>}
    </section>
  );
}

type RowProps = { label?: ReactNode; htmlFor?: string; stacked?: boolean; children: ReactNode };

// Label on the left and control on the right on wide screens; stacked on phones or when asked.
function Row({ label, htmlFor, stacked, children }: RowProps) {
  const wide = useWideLayout();
  const side = wide && !stacked;
  return (
    <div data-row className={`min-h-11 px-4 py-2.5 ${side ? "grid grid-cols-[minmax(12rem,1fr)_minmax(0,1.4fr)] items-center gap-6" : "flex flex-col gap-2"}`}>
      {label !== undefined && (
        htmlFor ? <label htmlFor={htmlFor} className="text-[15px]">{label}</label> : <div className="text-[15px]">{label}</div>
      )}
      <div className="min-w-0">{children}</div>
    </div>
  );
}

InsetGroup.Row = Row;
export default InsetGroup;
