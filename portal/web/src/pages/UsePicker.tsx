import { Button, Card, Input, Label, TextField } from "@heroui/react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { getUseGroups, type UseGroup } from "../api";
import { loadAnswers, saveAnswers } from "../screener";

export default function UsePicker() {
  const navigate = useNavigate();
  const [groups, setGroups] = useState<UseGroup[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    getUseGroups().then((g) => {
      if (g === "not_approved") setProblem("This list isn't ready yet. Please contact the Town Office.");
      else if (g === "busy") setProblem("Please wait a minute and try again.");
      else if (g === "invalid") setProblem("Something went wrong. Please start again.");
      else if (g === "unavailable") setProblem("We couldn't reach the Town's server. Please try again.");
      else setGroups(g);
    });
  }, []);

  const q = query.trim().toLowerCase();
  const shown = useMemo(() => {
    if (!groups) return [];
    if (q) {
      const hits = groups.flatMap((g) => g.uses).filter((u) =>
        [u.code_name, u.example, u.definition].some((t) => t.toLowerCase().includes(q)));
      return [{ key: "search", plain: "Matches", uses: hits }];
    }
    return groups.filter((g) => g.key === open);
  }, [groups, q, open]);

  function choose(useKey: string) {
    const answers = loadAnswers();
    if (answers) saveAnswers({ ...answers, use_key: useKey });
    navigate("/start/results");
  }

  if (problem) return <p role="alert">{problem}</p>;
  if (!groups) return <p>Loading…</p>;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">What will the land or building be used for?</h1>
      <TextField value={query} onChange={setQuery}>
        <Label>Search uses</Label>
        <Input />
      </TextField>
      {!q && (
        <div className="flex flex-wrap gap-2">
          {groups.map((g) => (
            <Button key={g.key} variant={open === g.key ? "primary" : "secondary"} onPress={() => setOpen(g.key)}>
              {g.plain}
            </Button>
          ))}
        </div>
      )}
      {shown.map((g) => (
        <div key={g.key} className="flex flex-col gap-2">
          {g.uses.length === 0 && <p>No uses match. Try another word, or pick a group.</p>}
          {g.uses.map((u) => (
            <Card key={u.use_key}>
              <Card.Header>
                <Card.Title>{u.code_name}</Card.Title>
                <Card.Description>{u.example}</Card.Description>
              </Card.Header>
              <Card.Content>
                <details>
                  <summary>What the Code says</summary>
                  <p className="text-sm">{u.definition}</p>
                </details>
              </Card.Content>
              <Card.Footer>
                <Button variant="primary" aria-label={`Choose ${u.code_name}`} onPress={() => choose(u.use_key)}>
                  Choose
                </Button>
              </Card.Footer>
            </Card>
          ))}
        </div>
      ))}
    </div>
  );
}
