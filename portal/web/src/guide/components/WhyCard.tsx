import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";

type Picture = { picture: ReactNode; pictureAlt: string } | { picture?: undefined; pictureAlt?: undefined };

// "Why" in the illustrated-house format (spec §6): the answer in one line, the detail after it,
// a picture where it helps, and the Code one tap away.
export function WhyCard({ overline, picture, pictureAlt, answer, detail, codeHref,
  codeLabel = "Read it in the Code" }: {
  overline: string; answer: string; detail: string; codeHref?: string; codeLabel?: string;
} & Picture) {
  return (
    <Card component="article">
      <CardContent sx={{ display: "grid", gap: 1 }}>
        <Typography variant="overline" color="primary" sx={{ lineHeight: 1.6 }}>{overline}</Typography>
        {picture && <div role="img" aria-label={pictureAlt}>{picture}</div>}
        <Typography variant="subtitle1" component="p" sx={{ fontWeight: 500 }}>{answer}</Typography>
        <Typography variant="body2" color="text.secondary">{detail}</Typography>
        {codeHref && <Link href={codeHref} underline="hover" sx={{ fontWeight: 500 }}>{codeLabel} ›</Link>}
      </CardContent>
    </Card>
  );
}
