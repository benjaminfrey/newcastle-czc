import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { IconPrinter } from "@tabler/icons-react";
import { useEffect, useState, type ReactNode } from "react";
import { useParams } from "react-router";
import { useWideLayout } from "../../shell/useWideLayout";
import { getPacket, isRefusal, type GuideRefusal, type Packet } from "../api";
import { distancesOf, DrawingList } from "../drawing/DrawingList";
import { LotDrawing } from "../drawing/LotDrawing";
import { GuideShell } from "../GuideShell";
import { GuideTheme } from "../theme/GuideTheme";
import { draftWording, fill, WORDS } from "../words";
import { PacketChecklist } from "./PacketChecklist";
import { PacketHistory } from "./PacketHistory";
import "./packet.css";

const P = WORDS.packet;
const DATE = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric" });

export function Part({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Box component="section" data-packet-part="" sx={{ display: "grid", gap: 1 }}>
      <Typography variant="h6" component="h2">{title}</Typography>
      {children}
    </Box>
  );
}

// The packet (guided plan 6; spec §7): what the Town will read about the project, in the spec's
// order, exactly as the API assembles it. The person's own words are shown as they wrote them.
function PacketScreen({ projectId }: { projectId: string }) {
  const [packet, setPacket] = useState<Packet | GuideRefusal | null>(null);
  const wide = useWideLayout();
  useEffect(() => {
    let live = true;
    void getPacket(projectId).then((p) => { if (live) setPacket(p); });
    return () => { live = false; };
  }, [projectId]);
  const back = { href: `/projects/${projectId}`, label: WORDS.back_to_project };

  if (packet === null || isRefusal(packet)) {
    const why = packet === "not_started" ? null : packet;
    return (
      <GuideShell title={P.title} back={back} draft={draftWording()}>
        {packet === null && <Typography role="status">{WORDS.loading}</Typography>}
        {why && typeof why === "string" && why in WORDS.refusals &&
          <Alert severity="info">{WORDS.refusals[why as keyof typeof WORDS.refusals]}</Alert>}
      </GuideShell>
    );
  }

  const s = packet.summary;
  const drawn = { checks: packet.checks, history: packet.history.map((h) => ({ shown: { turn_id: h.turn_id }, value: h.value })) };
  const lot = (
    <Part title={P.drawing}>
      {packet.drawing?.outline
        ? <><LotDrawing drawing={packet.drawing} distances={distancesOf(drawn)} asking={null} />
          <DrawingList drawing={packet.drawing} guide={drawn} /></>
        : <Typography variant="body2">{P.no_drawing}</Typography>}
    </Part>
  );
  return (
    <GuideShell title={P.title} back={back} draft={draftWording(packet.drafts)}
      actions={<Button onClick={() => window.print()} startIcon={<IconPrinter size={20} aria-hidden="true" />}
        sx={{ minHeight: 48 }}>{P.print}</Button>}>
      <Box data-packet="" sx={{ display: "grid", gap: 3 }}>
        <Box>
          <Typography variant="overline" color="text.secondary">
            {packet.state === "sent" && packet.sent_at ? fill(P.sent, { date: DATE.format(new Date(packet.sent_at)) }) : P.now}
          </Typography>
          <Typography variant="body2" color="text.secondary">{P.intro}</Typography>
          {!packet.finished && <Typography variant="body2">{P.not_finished}</Typography>}
        </Box>

        {s.corrections.lot_disputed && (
          <Alert severity="warning">
            {WORDS.unsettled.lot_disputed}
            {s.corrections.note && <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{s.corrections.note}</Typography>}
          </Alert>
        )}

        <Part title={P.own_words}>
          {s.own_words.length === 0
            ? <Typography variant="body2" color="text.secondary">{P.no_words}</Typography>
            : s.own_words.map((w, i) => (
              <Box key={i} component="blockquote" sx={{ m: 0, pl: 1.5, borderLeft: 3, borderColor: "divider" }}>
                <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>{w.body}</Typography>
              </Box>
            ))}
        </Part>
        <Part title={P.reading}>
          <Typography variant="body1">{s.reading ?? WORDS.unknown}</Typography>
        </Part>
        <Part title={P.deciders}>
          {s.deciders.length === 0
            ? <Typography variant="body1">{P.no_deciders}</Typography>
            : s.deciders.map((d) => <Typography key={d} variant="body1">{d}</Typography>)}
        </Part>
        <Part title={P.history}><PacketHistory history={packet.history} /></Part>
        {wide
          ? <Box sx={{ display: "grid", gridTemplateColumns: "minmax(0, 3fr) minmax(0, 2fr)", gap: 3, alignItems: "start" }}>
              <Part title={P.checklist}><PacketChecklist checklist={packet.checklist} /></Part>
              {lot}
            </Box>
          : <><Part title={P.checklist}><PacketChecklist checklist={packet.checklist} /></Part>{lot}</>}
      </Box>
    </GuideShell>
  );
}

export default function PacketPage() {
  const { id } = useParams();
  return <GuideTheme><PacketScreen projectId={id ?? ""} /></GuideTheme>;
}
