import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import ScopedCssBaseline from "@mui/material/ScopedCssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import { useMemo, type ReactNode } from "react";
import { createGuideTheme } from "./theme";
import type { GuideTokens } from "./tokens";

// The guide's theme and baseline, scoped to its own subtree so the HeroUI pages keep their look
// until the public launch retires them (spec decision 13).
export function GuideTheme({ tokens, children }: { tokens?: GuideTokens; children: ReactNode }) {
  const theme = useMemo(() => createGuideTheme(tokens), [tokens]);
  return (
    <ThemeProvider theme={theme}>
      <ScopedCssBaseline>{children}</ScopedCssBaseline>
    </ThemeProvider>
  );
}
