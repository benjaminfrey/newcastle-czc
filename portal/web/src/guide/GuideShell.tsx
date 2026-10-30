import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import { IconArrowLeft, IconHelpCircle } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useWideLayout } from "../shell/useWideLayout";
import { StepBar } from "./components/StepBar";

type Props = {
  title: string;
  back?: { href: string; label: string };
  helpHref?: string;
  draft?: boolean;                                    // wording not yet approved by the chair
  step?: { step: number; of: number; label: string };
  aside?: ReactNode;                                  // the project summary and lot drawing
  children: ReactNode;                                // the conversation
};

// The guided builder's window (spec §4.8): one column on a phone; on a computer (≥ 1024 px) the
// conversation on the left and the project on the right.
export function GuideShell({ title, back, helpHref, draft, step, aside, children }: Props) {
  const wide = useWideLayout();
  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default", color: "text.primary" }}>
      <AppBar position="sticky" color="inherit" elevation={0}
        sx={{ bgcolor: "background.default", borderBottom: 1, borderColor: "divider" }}>
        <Toolbar sx={{ gap: 1, maxWidth: 1120, width: "100%", mx: "auto" }}>
          {back && (
            <IconButton component={Link} to={back.href} aria-label={`Back to ${back.label}`} edge="start" sx={{ width: 48, height: 48 }}>
              <IconArrowLeft size={22} aria-hidden="true" />
            </IconButton>
          )}
          <Typography variant="h6" component="h1" sx={{ flex: 1, minWidth: 0 }} noWrap>{title}</Typography>
          {draft && <Chip size="small" label="Draft wording, not approved" color="warning" variant="outlined" />}
          {helpHref && (
            <IconButton component={Link} to={helpHref} aria-label="Help" sx={{ width: 48, height: 48 }}>
              <IconHelpCircle size={22} aria-hidden="true" />
            </IconButton>
          )}
        </Toolbar>
        {step && <Box sx={{ px: 2, pb: 1.5, maxWidth: 1120, width: "100%", mx: "auto" }}><StepBar {...step} /></Box>}
      </AppBar>
      <Box sx={{
        maxWidth: 1120, mx: "auto", px: 2, py: 2, display: "grid", gap: 3, alignItems: "start",
        gridTemplateColumns: wide && aside ? "minmax(0, 1fr) 340px" : "minmax(0, 1fr)",
      }}>
        <Box component="main" sx={{ display: "flex", flexDirection: "column", gap: 1.5, minWidth: 0, maxWidth: 680 }}>
          {children}
        </Box>
        {aside && <Box component="aside" aria-label="Your project" sx={{ minWidth: 0 }}>{aside}</Box>}
      </Box>
    </Box>
  );
}
