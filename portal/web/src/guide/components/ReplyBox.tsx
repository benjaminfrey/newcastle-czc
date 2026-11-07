import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { IconSend } from "@tabler/icons-react";
import { useState, type FormEvent } from "react";

// A box to say more in the person's own words. Enter sends; a blank box can't be sent. When
// onSend says the text wasn't kept (false), it stays in the box.
export function ReplyBox({ placeholder, onSend, initial = "" }: {
  placeholder: string; onSend: (text: string) => void | boolean | Promise<boolean>; initial?: string;
}) {
  const [text, setText] = useState(initial);
  const blank = text.trim() === "";
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (blank) return;
    const sent = text;
    if ((await onSend(sent.trim())) === false) return;
    setText((now) => (now === sent ? "" : now));
  };
  return (
    <Stack component="form" direction="row" onSubmit={(e) => void submit(e)} sx={{ gap: 1, alignItems: "center" }}>
      <TextField fullWidth value={text} onChange={(e) => setText(e.target.value)}
        placeholder={placeholder} slotProps={{ htmlInput: { "aria-label": placeholder } }}
        sx={(t) => ({ "& .MuiOutlinedInput-root": { borderRadius: `${t.guide.radius.full}px` } })} />
      <IconButton type="submit" aria-label="Send" disabled={blank} color="primary" sx={{ width: 48, height: 48 }}>
        <IconSend size={22} aria-hidden="true" />
      </IconButton>
    </Stack>
  );
}
