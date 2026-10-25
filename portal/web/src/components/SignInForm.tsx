import { Button, Description, Form, Input, Label, TextField } from "@heroui/react";
import { useState, type FormEvent } from "react";
import { requestLink, UNREACHABLE, type LinkResult } from "../api";

const MESSAGES: Record<Exclude<LinkResult, "sent">, string> = {
  too_many_requests:
    "You've asked for several links in the last hour. If one has arrived, use the newest email. Otherwise, please wait a while and try again.",
  email_unavailable: "We couldn't send the email just now. Please try again in a few minutes.",
  invalid_email: "That doesn't look like an email address. Please check it and try again.",
  unreachable: UNREACHABLE,
};

// Ask for an email address, send a sign-in link, then say where it went and for how long it
// works. Used by the sign-in page and the sheet on "What you'll need".
export default function SignInForm() {
  const [email, setEmail] = useState("");
  const [result, setResult] = useState<LinkResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function send() {
    setBusy(true);
    try {
      setResult(await requestLink(email));
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send();
  }

  if (result === "sent") {
    return (
      <div className="flex flex-col gap-3 rounded-xl bg-[var(--app-row)] p-5">
        <h2 className="text-[20px] font-medium leading-[1.3]">Check your email</h2>
        <p>We sent a sign-in link to <strong>{email}</strong>. The link works once, for 15 minutes, and brings you back here.</p>
        <p className="text-[15px] text-[var(--app-secondary-label)]">Didn't get it? Check your junk mail, or send another.</p>
        <div><Button variant="secondary" className="min-h-11" isDisabled={busy} onPress={() => void send()}>Send it again</Button></div>
      </div>
    );
  }
  return (
    <Form onSubmit={onSubmit} className="flex flex-col gap-4 rounded-xl bg-[var(--app-row)] p-5">
      <TextField type="email" isRequired value={email} onChange={setEmail} autoComplete="email">
        <Label>Your email address</Label>
        <Input className="min-h-11" />
        <Description>No password needed. We only use it to send you links and updates about your applications.</Description>
      </TextField>
      {result && <p role="alert" className="text-[var(--app-destructive)]">{MESSAGES[result]}</p>}
      <button type="submit" className="btn btn-filled self-start" disabled={busy}>Email me a sign-in link</button>
    </Form>
  );
}
