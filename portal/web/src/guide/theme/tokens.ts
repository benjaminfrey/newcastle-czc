// The guided builder's look, as named settings (spec §10.2). Every color, font, corner and
// spacing value under src/guide/ comes from here, so the look can change without touching a
// screen. Behavior is not a token: there is one way to ask and move around.
//
// The palette is Material's tonal scheme built on the Town seal's teal (#0C727E, the portal's
// accent since the 2026-10-23 redesign).

export type GuidePalette = {
  primary: string; onPrimary: string; primaryContainer: string; onPrimaryContainer: string;
  surface: string; surfaceContainer: string; onSurface: string; onSurfaceVariant: string;
  outline: string; outlineVariant: string;
  error: string; success: string; warning: string;
};

export type GuideTokens = {
  color: { light: GuidePalette; dark: GuidePalette };
  font: { body: string; display: string };
  radius: { small: number; medium: number; large: number; full: number };
  spacing: number; // px per MUI spacing unit
};

const ROBOTO = 'Roboto, "Helvetica Neue", Arial, system-ui, sans-serif';

export const newcastleTokens: GuideTokens = {
  color: {
    light: {
      primary: "#0C727E", onPrimary: "#FFFFFF", primaryContainer: "#A6EEF8", onPrimaryContainer: "#001F24",
      surface: "#F5FAFB", surfaceContainer: "#E9EFF0", onSurface: "#171D1E", onSurfaceVariant: "#3F484A",
      outline: "#6F797A", outlineVariant: "#BFC8CA",
      error: "#BA1A1A", success: "#1B7A31", warning: "#8A4B00",
    },
    dark: {
      primary: "#82D3E0", onPrimary: "#00363D", primaryContainer: "#004F58", onPrimaryContainer: "#A6EEF8",
      surface: "#0E1415", surfaceContainer: "#1B2122", onSurface: "#DEE3E5", onSurfaceVariant: "#BFC8CA",
      outline: "#899294", outlineVariant: "#3F484A",
      error: "#FFB4AB", success: "#6FD089", warning: "#FFC266",
    },
  },
  font: { body: ROBOTO, display: ROBOTO },
  radius: { small: 8, medium: 12, large: 16, full: 999 },
  spacing: 8,
};
