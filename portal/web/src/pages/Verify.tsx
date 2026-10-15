import { Button, Card } from "@heroui/react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { verifyToken } from "../api";

// Pure, so React may call it twice in development (StrictMode) and get the same answer.
function tokenFromUrl(): string | null {
  return new URLSearchParams(window.location.hash.slice(1)).get("token");
}

export default function Verify() {
  const navigate = useNavigate();
  const [token] = useState(tokenFromUrl);
  const [failed, setFailed] = useState(!token);
  const [busy, setBusy] = useState(false);

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
    const me = await verifyToken(token);
    if (me) navigate("/my-applications", { replace: true });
    else setFailed(true);
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
      <Card.Footer>
        <Button variant="primary" onPress={signIn} isDisabled={busy}>Sign me in</Button>
      </Card.Footer>
    </Card>
  );
}
