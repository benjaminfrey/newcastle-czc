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
import { GuideTheme } from "./theme/GuideTheme";

// The chosen mockup (Material, 2026-10-30) made real, with its draft wording. No server calls:
// it shows the look and the pieces. D4's two-story limit here is sketch data, not the ruleset.
const ANSWERS = [
  { id: "yes", label: "Yes, inside the roof", hint: "like a finished attic" },
  { id: "no", label: "No, it has full walls" },
  { id: "unsure", label: "I'm not sure yet" },
];

function Attic() {
  const v = (name: string) => `var(--mui-palette-${name})`;
  return (
    <svg viewBox="0 0 300 120" width="100%" aria-hidden="true">
      <rect x="70" y="58" width="120" height="56" fill={v("background-default")} stroke={v("text-secondary")} strokeWidth="2" />
      <line x1="70" y1="86" x2="190" y2="86" stroke={v("text-secondary")} strokeWidth="1.5" />
      <path d="M60 58 L130 10 L200 58 Z" fill={v("primaryContainer")} stroke={v("primary-main")} strokeWidth="2" />
      <rect x="112" y="34" width="36" height="16" fill={v("background-default")} stroke={v("primary-main")} strokeWidth="1.5" />
      <text x="210" y="38" fontSize="11" fill={v("primary-main")}>inside roof:</text>
      <text x="210" y="51" fontSize="11" fill={v("primary-main")}>not counted</text>
      <text x="210" y="76" fontSize="11" fill={v("text-primary")}>2nd story ✓</text>
      <text x="210" y="104" fontSize="11" fill={v("text-primary")}>1st story ✓</text>
    </svg>
  );
}

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
        <WhyCard overline="Why · how stories are counted" picture={<Attic />}
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
