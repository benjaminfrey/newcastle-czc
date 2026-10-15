import { Button, Card, Description, Form, Input, Label, TextField } from "@heroui/react";
import { useState, type FormEvent } from "react";
import { requestLink, type LinkResult } from "../api";

const MESSAGES: Record<Exclude<LinkResult, "sent">, string> = {
  too_many_requests: "You've asked for several links in the last hour. Please wait a while and try again.",
  email_unavailable: "We couldn't send the email just now. Please try again in a few minutes.",
  invalid_email: "That doesn't look like an email address. Please check it and try again.",
};

export default function SignIn() {
  const [email, setEmail] = useState("");
  const [result, setResult] = useState<LinkResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setResult(await requestLink(email));
    setBusy(false);
  }

  if (result === "sent") {
    return (
      <Card>
        <Card.Header>
          <Card.Title>Check your email</Card.Title>
          <Card.Description>
            We sent a sign-in link to {email}. It works once and stops working after 15 minutes.
          </Card.Description>
        </Card.Header>
      </Card>
    );
  }

  return (
    <Card>
      <Card.Header>
        <Card.Title>Sign in</Card.Title>
        <Card.Description>No password needed. We'll email you a link.</Card.Description>
      </Card.Header>
      <Card.Content>
        <Form onSubmit={onSubmit} className="flex flex-col gap-4">
          <TextField type="email" isRequired value={email} onChange={setEmail}>
            <Label>Your email address</Label>
            <Input />
            <Description>We only use it to send you links and updates about your applications.</Description>
          </TextField>
          {result && <p role="alert">{MESSAGES[result]}</p>}
          <Button type="submit" variant="primary" isDisabled={busy}>Email me a sign-in link</Button>
        </Form>
      </Card.Content>
    </Card>
  );
}
