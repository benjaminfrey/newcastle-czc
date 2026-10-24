import { Disclosure } from "@heroui/react";
import { citeLabel } from "../screener";

// "Why we ask": the Code section a question rests on, in the Code's own words.
export default function WhyWeAsk({ why }: { why: { cite: string; text: string } | null }) {
  if (!why) return null;
  return (
    <Disclosure>
      <Disclosure.Heading>
        <Disclosure.Trigger className="inline-flex min-h-11 flex-row items-center gap-1 text-[15px] text-[var(--app-accent-text)]">
          Why we ask
          <Disclosure.Indicator className="size-4" />
        </Disclosure.Trigger>
      </Disclosure.Heading>
      <Disclosure.Content>
        <Disclosure.Body>
          <div className="rounded-lg bg-[var(--app-ground)] p-3">
            <p className="text-[13px] font-semibold">{citeLabel(why.cite)}</p>
            <p className="whitespace-pre-line text-[13px] text-[var(--app-secondary-label)]">{why.text}</p>
          </div>
        </Disclosure.Body>
      </Disclosure.Content>
    </Disclosure>
  );
}
