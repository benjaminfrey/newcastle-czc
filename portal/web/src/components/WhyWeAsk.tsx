import { Disclosure } from "@heroui/react";
import { citeLabel } from "../screener";

// "Why we ask": the Code section a question rests on, in the Code's own words.
export default function WhyWeAsk({ why }: { why: { cite: string; text: string } | null }) {
  if (!why) return null;
  return (
    <Disclosure>
      <Disclosure.Heading>
        <Disclosure.Trigger className="underline">
          Why we ask
          <Disclosure.Indicator />
        </Disclosure.Trigger>
      </Disclosure.Heading>
      <Disclosure.Content>
        <Disclosure.Body>
          <p className="text-sm font-semibold">{citeLabel(why.cite)}</p>
          <p className="text-sm whitespace-pre-line">{why.text}</p>
        </Disclosure.Body>
      </Disclosure.Content>
    </Disclosure>
  );
}
