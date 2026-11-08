import type { Entry } from "../api";
import { PICTURES } from "../pictures";
import { LW } from "../../library/words";
import { WhyCard } from "./WhyCard";

// A library entry as its "Why" card, with its picture when it has one (guided plan 5).
// A number resting on the chair's recorded reading carries the Town's-interpretation mark (design 2, decision 16).
export function entryCard(e: Entry) {
  const Picture = e.picture ? PICTURES[e.picture] : undefined;
  const note = e.interpretations?.length ? LW.interpretation_mark : undefined;
  return Picture && e.picture_alt
    ? <WhyCard key={e.id} overline={e.overline} answer={e.answer} detail={e.detail} note={note} picture={<Picture />} pictureAlt={e.picture_alt} />
    : <WhyCard key={e.id} overline={e.overline} answer={e.answer} detail={e.detail} note={note} />;
}
