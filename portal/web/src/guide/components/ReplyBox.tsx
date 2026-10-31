import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { IconSend } from "@tabler/icons-react";
import { useState, type FormEvent } from "react";

// A box to say more in the person's own words. Enter sends; a blank box can't be sent.
export function ReplyBox({ placeholder, onSend }: { placeholder: string; onSend: (text: string) => void }) {
  const [text, setText] = useState("");
  const blank = text.trim() === "";
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (blank) return;
    onSend(text.trim());
    setText("");
  };
  return (
    <Stack component="form" direction="row" onSubmit={submit} sx={{ gap: 1, alignItems: "center" }}>
      <TextField fullWidth value={text} onChange={(e) => setText(e.target.value)}
        placeholder={placeholder} slotProps={{ htmlInput: { "aria-label": placeholder } }}
        sx={(t) => ({ "& .MuiOutlinedInput-root": { borderRadius: `${t.guide.radius.full}px` } })} />
      <IconButton type="submit" aria-label="Send" disabled={blank} color="primary" sx={{ width: 48, height: 48 }}>
        <IconSend size={22} aria-hidden="true" />
      </IconButton>
    </Stack>
  );
}
