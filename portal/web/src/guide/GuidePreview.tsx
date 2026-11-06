import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import { useState } from "react";
import { AnswerList } from "./components/AnswerList";
import { Bubble } from "./components/Bubble";
import { ReplyBox } from "./components/ReplyBox";
import { SuggestionChips } from "./components/SuggestionChips";
import { WhyCard } from "./components/WhyCard";
import { GuideShell } from "./GuideShell";
import { StoriesPicture } from "./pictures/StoriesPicture";
import { GuideTheme } from "./theme/GuideTheme";

// The chosen mockup (Material, 2026-10-30) made real, with its draft wording. No server calls:
// it shows the look and the pieces. D4's two-story limit here is sketch data, not the ruleset.
const ANSWERS = [
  { id: "yes", label: "Yes, inside the roof", hint: "like a finished attic" },
  { id: "no", label: "No, it has full walls" },
  { id: "unsure", label: "I'm not sure yet" },
];

export default function GuidePreview() {
  const [said, setSaid] = useState<string[]>([]);
  const answer = (id: string) => setSaid((s) => [...s, ANSWERS.find((a) => a.id === id)!.label]);
  return (
    <GuideTheme>
      <GuideShell title="Your new house" back={{ href: "/", label: "Home" }} draft
        step={{ step: 3, of: 6, label: "The building" }}
        aside={<Card><CardContent sx={{ display: "grid", gap: 0.5 }}>
          <Typography variant="overline" color="text.secondary">Your project</Typography>
          <Typography variant="subtitle1" component="p" sx={{ fontWeight: 500 }}>A new house</Typography>
          <Typography variant="body2" color="text.secondary">
            Sketch data for this preview. The project summary and lot drawing go here.</Typography>
        </CardContent></Card>}>
        <Bubble from="you">I want to build a 3-story house.</Bubble>
        <Bubble from="app">Good news: this may fit. In D4 a house can have 2 stories, but{" "}
          <b>a floor inside the roof doesn't count.</b></Bubble>
        <WhyCard overline="Why · how stories are counted" picture={<StoriesPicture />}
          pictureAlt="A house with two full stories and a floor inside the roof; the floor inside the roof is not counted"
          answer="Only floors with full-height outside walls count."
          detail="A finished attic or a floor tucked under the roof slope doesn't count toward the limit." />
        <AnswerList question="Is your third floor inside the roof?" answers={ANSWERS} onAnswer={answer} />
        {said.map((s, i) => <Bubble key={i} from="you">{s}</Bubble>)}
        <SuggestionChips onChip={() => {}}
          chips={[{ id: "roofs", label: "Compare roof shapes" }, { id: "town", label: "Ask the Town Office" }]} />
        <ReplyBox placeholder="Or tell us more…" onSend={(t) => setSaid((s) => [...s, t])} />
      </GuideShell>
    </GuideTheme>
  );
}
