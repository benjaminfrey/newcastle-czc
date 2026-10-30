import Box from "@mui/material/Box";
import type { ReactNode } from "react";

const visuallyHidden = { position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" } as const;

// One turn of the conversation: the person's words on the right, Newcastle's on the left.
export function Bubble({ from, children }: { from: "you" | "app"; children: ReactNode }) {
  const you = from === "you";
  return (
    <Box sx={(t) => ({
      alignSelf: you ? "flex-end" : "flex-start", maxWidth: "88%", px: 2, py: 1.25,
      borderRadius: you ? "20px 20px 4px 20px" : "4px 20px 20px 20px",
      background: you ? t.vars?.palette.primary.main : t.vars?.palette.surfaceContainer,
      color: you ? t.vars?.palette.primary.contrastText : t.vars?.palette.text.primary,
    })}>
      <Box component="span" sx={visuallyHidden}>{you ? "You said" : "Newcastle"}</Box>
      {children}
    </Box>
  );
}
