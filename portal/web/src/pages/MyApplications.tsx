import { Button, Card } from "@heroui/react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { getMe, signOut, type Me } from "../api";

export default function MyApplications() {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    getMe().then((m) => (m ? setMe(m) : navigate("/signin", { replace: true })));
  }, [navigate]);

  if (!me) return <p>Loading…</p>;
  return (
    <Card>
      <Card.Header>
        <Card.Title>My applications</Card.Title>
        <Card.Description>Signed in as {me.email}</Card.Description>
      </Card.Header>
      <Card.Content>
        <p>You haven't started any applications yet.</p>
      </Card.Content>
      <Card.Footer>
        <Button variant="secondary" onPress={() => signOut().then(() => navigate("/", { replace: true }))}>
          Sign out
        </Button>
      </Card.Footer>
    </Card>
  );
}
