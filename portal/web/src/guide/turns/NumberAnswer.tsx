import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { IconMinus, IconPlus } from "@tabler/icons-react";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { checkValue, isRefusal, type Check, type Entry, type Shown } from "../api";
import { WhyCard } from "../components/WhyCard";
import { fill, WORDS } from "../words";
import { TURN_HEADING } from "./heading";

type Props = { shown: Shown; projectId: string; busy: boolean; locked: boolean; onAnswer: (value: unknown) => void };

// "1,800", " 25 " and "25.5" are numbers; "" is nothing yet; anything else isn't a number.
export function parseNumber(text: string): number | null | "not_a_number" {
  const t = text.trim();
  if (t === "") return null;
  if (!/^\d{1,3}(,\d{3})+(\.\d+)?$|^\d+(\.\d+)?$|^\.\d+$/.test(t)) return "not_a_number";
  return Number(t.replace(/,/g, ""));
}

const fmt = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 2 });
const words = (s: string) => s.replace(/\s+/g, " ").trim();

// The words under the field: what the API's check says, never a verdict of our own (spec §5).
function roomWords(c: Check, unit: string): string {
  if (c.result === "fits") return c.room === 0 ? WORDS.at_limit : words(fill(WORDS.room_left, { room: fmt(c.room ?? 0), unit }));
  if (c.result === "outside") {
    return words(fill(c.direction === "short" ? WORDS.past_limit_short : WORDS.past_limit_over, { gap: fmt(c.gap ?? 0), unit }));
  }
  return WORDS.town_decides;
}

const card = (e: Entry) => <WhyCard key={e.id} overline={e.overline} answer={e.answer} detail={e.detail} />;

// A number turn (spec §4.4): a field with steppers, and, once the limit is known, a slider marked
// at it. As the value changes the API checks it (debounced) and the line under the field shows
// the room left. A number past its limit is shown in plain words, never as an error; only input
// the question can't take (not a number, outside its range) is an error.
export function NumberAnswer({ shown, projectId, busy, locked, onAnswer }: Props) {
  const input = shown.input ?? { unit: null, min: 0, max: Number.MAX_SAFE_INTEGER };
  const headingId = useId();
  const helpId = useId();
  const [text, setText] = useState("");
  const [checked, setChecked] = useState<{ value: number; check: Check } | null>(null);
  const [bounds, setBounds] = useState<number[]>([]);
  const seq = useRef(0);
  const parsed = parseNumber(text);
  const value = typeof parsed === "number" ? parsed : null;
  const inputError = parsed === "not_a_number" ? WORDS.not_a_number
    : value != null && (value < input.min || value > input.max) ? WORDS.out_of_range : null;
  const usable = value != null && !inputError;
  const unit = input.unit ?? checked?.check.unit ?? "";

  useEffect(() => {
    if (!usable || value == null) return;
    const mine = ++seq.current;
    const abort = new AbortController();
    const t = setTimeout(async () => {
      const out = await checkValue(projectId, shown.turn_id, value, abort.signal);
      if (mine !== seq.current || isRefusal(out) || out.result === null) return;
      setChecked({ value, check: out });
      const b = [out.min, out.max].filter((n): n is number => n != null);
      if (b.length) setBounds(b);
    }, 300);
    return () => { clearTimeout(t); abort.abort(); };
  }, [usable, value, projectId, shown.turn_id]);

  const set = (n: number) => setText(String(Math.min(input.max, Math.max(input.min, n))));
  const step = (by: number) => set(value == null ? input.min : value + by);
  const top = bounds.length ? Math.min(input.max, Math.max(...bounds) * 2 || input.min + 10) : null;
  const shownCheck = checked && checked.value === value && !inputError ? checked.check : null;
  const off = busy || locked;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (usable && !off) onAnswer(value);
  };

  return (
    <Box component="section" data-turn={shown.turn_id} sx={{ display: "grid", gap: 1.5 }}>
      <Typography id={headingId} variant="subtitle1" component="h2" sx={{ fontWeight: 500 }} {...TURN_HEADING}>
        {shown.ask}
      </Typography>
      {shown.help && <Typography variant="body2" color="text.secondary">{shown.help}</Typography>}
      {shown.defines.map(card)}
      {shown.why && card(shown.why)}
      <Box component="form" onSubmit={submit} sx={{ display: "grid", gap: 1.5 }}>
        <Stack direction="row" sx={{ gap: 1, alignItems: "flex-start" }}>
          <IconButton aria-label={WORDS.less} onClick={() => step(-1)} disabled={off} sx={{ width: 48, height: 48, mt: 0.5 }}>
            <IconMinus size={20} aria-hidden="true" />
          </IconButton>
          <TextField fullWidth value={text} onChange={(e) => setText(e.target.value)} disabled={locked}
            error={!!inputError} helperText={inputError ?? " "}
            slotProps={{
              htmlInput: { inputMode: "decimal", "aria-labelledby": headingId, "aria-describedby": helpId, autoComplete: "off" },
              input: unit ? { endAdornment: <InputAdornment position="end">{unit}</InputAdornment> } : undefined,
            }} />
          <IconButton aria-label={WORDS.more} onClick={() => step(1)} disabled={off} sx={{ width: 48, height: 48, mt: 0.5 }}>
            <IconPlus size={20} aria-hidden="true" />
          </IconButton>
        </Stack>
        <Typography id={helpId} role="status" variant="body2" color="text.secondary" sx={{ minHeight: "1.5em" }}>
          {shownCheck ? roomWords(shownCheck, unit) : ""}
        </Typography>
        {top != null && (
          <Box sx={{ px: 1.5 }}>
            <Slider value={value != null && !inputError ? Math.min(value, top) : input.min} min={input.min} max={top}
              step={1} disabled={off} onChange={(_, v) => set(v as number)}
              marks={bounds.map((b) => ({ value: b, label: WORDS.limit_mark }))}
              slotProps={{ input: { "aria-labelledby": headingId } }} />
          </Box>
        )}
        <Stack direction="row" sx={{ gap: 1, flexWrap: "wrap" }}>
          <Button type="submit" variant="contained" disabled={!usable || off} sx={{ minHeight: 48, px: 3 }}>{WORDS.next}</Button>
          <Button variant="text" disabled={off} onClick={() => onAnswer("unsure")} sx={{ minHeight: 48 }}>{WORDS.unsure}</Button>
        </Stack>
      </Box>
    </Box>
  );
}
