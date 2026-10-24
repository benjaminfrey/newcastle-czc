// The portal's colours, light and dark: Apple's system greys and grouped grounds, with the
// Town seal's teal. The seal's own teal (#1098A8, about 3.4:1 on white) marks identity and
// selection; a deeper teal of the same hue carries buttons and links. index.css declares the
// same values as --app-* custom properties (a test keeps them in step).

export type Tokens = {
  ground: string; groupedGround: string; row: string; separator: string;
  label: string; secondaryLabel: string; tertiaryLabel: string;
  accent: string; accentText: string; onAccent: string;
  seal: string; destructive: string; selection: string;
  // A field's fill (iOS tertiary fill, made opaque), and a sheet's raised ground and rows: in dark
  // mode a sheet is lighter than the window under it, as on iOS.
  fill: string; groundElevated: string; rowElevated: string;
};

export const LIGHT: Tokens = {
  ground: "#F2F2F7", groupedGround: "#F2F2F7", row: "#FFFFFF", separator: "#C6C6C8",
  label: "#1C1C1E", secondaryLabel: "#636366", tertiaryLabel: "#8A8A8E",
  accent: "#0C727E", accentText: "#0C727E", onAccent: "#FFFFFF",
  seal: "#1098A8", destructive: "#D70015", selection: "#DCEFF1",
  fill: "#EEEEF0", groundElevated: "#F2F2F7", rowElevated: "#FFFFFF",
};

export const DARK: Tokens = {
  ground: "#000000", groupedGround: "#000000", row: "#1C1C1E", separator: "#38383A",
  label: "#F2F2F7", secondaryLabel: "#AEAEB2", tertiaryLabel: "#8A8A8E",
  accent: "#0C727E", accentText: "#4CC9D8", onAccent: "#FFFFFF",
  seal: "#1098A8", destructive: "#FF6961", selection: "#123C42",
  fill: "#3A3A3C", groundElevated: "#1C1C1E", rowElevated: "#2C2C2E",
};

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

// WCAG 2.1 contrast ratio between two #RRGGBB colours.
export function contrast(fg: string, bg: string): number {
  const [hi, lo] = [luminance(fg), luminance(bg)].sort((a, b) => b - a);
  return (hi + 0.05) / (lo + 0.05);
}
