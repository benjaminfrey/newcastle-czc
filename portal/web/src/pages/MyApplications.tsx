import { Button, Card } from "@heroui/react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { getMe, signOut, UNREACHABLE, type Me } from "../api";
import { listApplications, type AppSummary } from "../applications";
import { longDate, mapLotLabel } from "../format";

export default function MyApplications() {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [list, setList] = useState<AppSummary[] | null>(null);

  useEffect(() => {
    getMe().then((m) => {
      if (m === "unavailable") setUnreachable(true);
      else if (m) {
        setMe(m);
        listApplications().then((l) => (typeof l === "string" ? setUnreachable(true) : setList(l)));
      } else navigate("/signin", { replace: true });
    });
  }, [navigate]);

  if (unreachable) return <p role="alert">{UNREACHABLE}</p>;
  if (!me) return <p>Loading…</p>;
  return (
    <Card>
      <Card.Header>
        <Card.Title>My applications</Card.Title>
        <Card.Description>Signed in as {me.email}</Card.Description>
      </Card.Header>
      <Card.Content>
        {list === null && <p>Loading…</p>}
        {list?.length === 0 && <p>You haven't started any applications yet.</p>}
        {list && list.length > 0 && (
          <ul className="flex flex-col gap-3">
            {list.map((a) => (
              <li key={a.id} className="flex flex-col gap-1">
                <span className="font-semibold">{a.official_title}</span>
                <span>{mapLotLabel(a.map_lot)} · Not sent yet · Last changed {longDate(a.updated_at)}</span>
                <Link to={`/applications/${a.id}`} className="underline">Continue</Link>
              </li>
            ))}
          </ul>
        )}
      </Card.Content>
      <Card.Footer>
        <Button variant="secondary" onPress={() => signOut().then(() => navigate("/", { replace: true }))}>
          Sign out
        </Button>
      </Card.Footer>
    </Card>
  );
}
