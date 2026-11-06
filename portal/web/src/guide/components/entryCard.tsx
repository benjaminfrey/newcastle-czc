import type { Entry } from "../api";
import { PICTURES } from "../pictures";
import { WhyCard } from "./WhyCard";

// A library entry as its "Why" card, with its picture when it has one (guided plan 5).
export function entryCard(e: Entry) {
  const Picture = e.picture ? PICTURES[e.picture] : undefined;
  return Picture && e.picture_alt
    ? <WhyCard key={e.id} overline={e.overline} answer={e.answer} detail={e.detail} picture={<Picture />} pictureAlt={e.picture_alt} />
    : <WhyCard key={e.id} overline={e.overline} answer={e.answer} detail={e.detail} />;
}
