import { Button, Card } from "@heroui/react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { getMe, UNREACHABLE, verifyToken } from "../api";
import { peekPendingStart } from "../pendingStart";

// Pure, so React may call it twice in development (StrictMode) and get the same answer.
function tokenFromUrl(): string | null {
  return new URLSearchParams(window.location.hash.slice(1)).get("token");
}

// After signing in, go back to the application the person was starting, if any.
function afterSignIn(): string {
  const pending = peekPendingStart();
  return pending ? `/apply/${pending.formKey}` : "/my-applications";
}

export default function Verify() {
  const navigate = useNavigate();
  const [token] = useState(tokenFromUrl);
  const [failed, setFailed] = useState(!token);
  const [busy, setBusy] = useState(false);
  const [unreachable, setUnreachable] = useState(false);

  // The token leaves the address bar and history at once; it lives only in memory
  // until the person presses the button.
  useEffect(() => {
    if (window.location.hash) history.replaceState(null, "", window.location.pathname + window.location.search);
  }, []);

  // Redeemed only on a click: mail scanners that run JavaScript open links too,
  // and must not use up a resident's link.
  async function signIn() {
    if (!token) return;
    setBusy(true);
    setUnreachable(false);
    try {
      const result = await verifyToken(token);
      if (result === "unavailable") {
        // The link may still be good: keep it and let the person press again.
        setUnreachable(true);
      } else if (result !== "invalid") {
        navigate(afterSignIn(), { replace: true });
      } else {
        // Already used in another tab? Then this person is signed in after all.
        const me = await getMe();
        if (me && me !== "unavailable") navigate(afterSignIn(), { replace: true });
        else setFailed(true);
      }
    } finally {
      setBusy(false);
    }
  }

  if (failed) {
    return (
      <Card>
        <Card.Header>
          <Card.Title>That link didn't work</Card.Title>
          <Card.Description>The link has expired or was already used. Sign-in links work once, for 15 minutes.</Card.Description>
        </Card.Header>
        <Card.Content>
          <Link to="/signin" className="underline">Get a new link</Link>
        </Card.Content>
      </Card>
    );
  }
  return (
    <Card>
      <Card.Header>
        <Card.Title>Sign in to Newcastle permits</Card.Title>
        <Card.Description>Press the button to finish signing in.</Card.Description>
      </Card.Header>
      {unreachable && (
        <Card.Content>
          <p role="alert">{UNREACHABLE}</p>
        </Card.Content>
      )}
      <Card.Footer>
        <Button variant="primary" onPress={signIn} isDisabled={busy}>Sign me in</Button>
      </Card.Footer>
    </Card>
  );
}
