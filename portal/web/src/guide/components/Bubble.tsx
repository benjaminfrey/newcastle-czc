import Box from "@mui/material/Box";
import type { ReactNode } from "react";

// Pixel sizes as strings: MUI's sx reads the number 1 as 100%.
const visuallyHidden = { position: "absolute", width: "1px", height: "1px", m: "-1px", p: 0, border: 0,
  overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap" } as const;

// One turn of the conversation: the person's words on the right, Newcastle's on the left.
export function Bubble({ from, children }: { from: "you" | "app"; children: ReactNode }) {
  const you = from === "you";
  return (
    <Box sx={(t) => ({
      alignSelf: you ? "flex-end" : "flex-start", maxWidth: "88%", px: 2, py: 1.25,
      borderRadius: ((l, sm) => (you ? `${l} ${l} ${sm} ${l}` : `${sm} ${l} ${l} ${l}`))(
        `${t.guide.radius.large}px`, `${t.guide.radius.small / 2}px`),
      background: you ? t.vars?.palette.primary.main : t.vars?.palette.surfaceContainer,
      color: you ? t.vars?.palette.primary.contrastText : t.vars?.palette.text.primary,
    })}>
      <Box component="span" sx={visuallyHidden}>{you ? "You said" : "Newcastle"}</Box>
      {children}
    </Box>
  );
}
