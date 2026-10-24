// Small roof silhouettes for the roof-style tiles (a picture says "gambrel" better than a word).
const PATHS: Record<string, string> = {
  gable: "M4 26 L24 8 L44 26",
  hipped: "M4 26 L16 10 L32 10 L44 26",
  gambrel: "M4 26 L10 14 L24 8 L38 14 L44 26",
  mansard: "M4 26 L8 12 L40 12 L44 26",
  shed: "M4 26 L4 10 L44 20 L44 26",
};

export default function RoofGlyph({ kind }: { kind: string }) {
  const d = PATHS[kind];
  if (!d) return null;
  return (
    <svg viewBox="0 0 48 32" className="h-8 w-12" aria-hidden="true">
      <rect x="8" y="24" width="32" height="6" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d={d} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
    </svg>
  );
}
