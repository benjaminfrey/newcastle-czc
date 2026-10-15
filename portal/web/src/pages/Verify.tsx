import { Card } from "@heroui/react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import { verifyToken } from "../api";

export default function Verify() {
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    // React StrictMode runs effects twice in development; a token works once.
    if (started.current) return;
    started.current = true;
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    // Remove the token from the address bar and history straight away.
    history.replaceState(null, "", window.location.pathname + window.location.search);
    if (!token) {
      setFailed(true);
      return;
    }
    verifyToken(token).then((me) => (me ? navigate("/my-applications", { replace: true }) : setFailed(true)));
  }, [navigate]);

  if (!failed) return <p>Signing you in…</p>;
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
