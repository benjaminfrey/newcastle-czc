// The guided builder's MUI theme, built only from tokens.ts.
//
// Material 3 in MUI 9.5 (spec §10.1, "builder to confirm"): MUI's components still follow
// Material Design 2 — elevation shadows on cards, 4 px corners, uppercase buttons, a single
// primary color with light/dark variants and no tonal "container" roles. The theme closes the
// gap with: custom palette roles for M3's containers and surfaces (augmented below), pill
// buttons in sentence case, 8 px chips, flat 12 px cards on tonal surfaces, and a rounded 4 px
// linear progress. That is enough to match the chosen mockup without a parallel component set.
import { createTheme, type Theme } from "@mui/material/styles";
import { newcastleTokens, type GuidePalette, type GuideTokens } from "./tokens";

declare module "@mui/material/styles" {
  interface Palette {
    primaryContainer: string; onPrimaryContainer: string;
    surfaceContainer: string; outlineVariant: string;
  }
  interface PaletteOptions {
    primaryContainer?: string; onPrimaryContainer?: string;
    surfaceContainer?: string; outlineVariant?: string;
  }
}

function palette(p: GuidePalette) {
  return {
    primary: { main: p.primary, contrastText: p.onPrimary },
    error: { main: p.error }, success: { main: p.success }, warning: { main: p.warning },
    background: { default: p.surface, paper: p.surface },
    text: { primary: p.onSurface, secondary: p.onSurfaceVariant },
    divider: p.outlineVariant,
    primaryContainer: p.primaryContainer, onPrimaryContainer: p.onPrimaryContainer,
    surfaceContainer: p.surfaceContainer, outlineVariant: p.outlineVariant,
  };
}

export function createGuideTheme(tokens: GuideTokens = newcastleTokens): Theme {
  const { radius } = tokens;
  return createTheme({
    // followDeviceScheme() (src/theme/colorScheme.ts) sets data-theme on <html>.
    cssVariables: { colorSchemeSelector: '[data-theme="%s"]' },
    colorSchemes: { light: { palette: palette(tokens.color.light) }, dark: { palette: palette(tokens.color.dark) } },
    shape: { borderRadius: radius.medium },
    spacing: tokens.spacing,
    typography: { fontFamily: tokens.font.body, button: { textTransform: "none", fontWeight: 500 } },
    components: {
      MuiButton: { styleOverrides: { root: { borderRadius: radius.full, minHeight: 48, paddingInline: 24 } } },
      MuiChip: { styleOverrides: { root: { borderRadius: radius.small, minHeight: 36 } } },
      MuiCard: {
        defaultProps: { elevation: 0 },
        styleOverrides: { root: ({ theme }) => ({ borderRadius: radius.medium, background: theme.vars?.palette.surfaceContainer }) },
      },
      MuiLinearProgress: {
        styleOverrides: {
          root: ({ theme }) => ({ height: 4, borderRadius: radius.small, background: theme.vars?.palette.primaryContainer }),
          bar: { borderRadius: radius.small },
        },
      },
      MuiListItemButton: { styleOverrides: { root: { minHeight: 48 } } },
    },
  });
}
