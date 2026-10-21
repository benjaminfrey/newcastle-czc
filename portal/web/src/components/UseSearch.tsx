import { Button, Card, Input, Label, TextField } from "@heroui/react";
import { useEffect, useMemo, useState } from "react";
import { getUseGroups, type UseGroup } from "../api";

type Props = {
  // Called with the use the person picks.
  onChoose: (useKey: string, codeName: string) => void;
  // Uses already picked, shown as such.
  chosen?: string[];
  chooseLabel?: string;
};

// The Code's uses, found by plain groups or by searching names, examples and the
// Code's definitions. Used by "Do I need a permit?" and by the application forms.
export default function UseSearch({ onChoose, chosen = [], chooseLabel = "Choose" }: Props) {
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

  if (problem) return <p role="alert">{problem}</p>;
  if (!groups) return <p>Loading…</p>;
  return (
    <div className="flex flex-col gap-4">
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
                {chosen.includes(u.use_key) ? (
                  <p className="font-semibold">Added</p>
                ) : (
                  <Button variant="primary" aria-label={`${chooseLabel} ${u.code_name}`} onPress={() => onChoose(u.use_key, u.code_name)}>
                    {chooseLabel}
                  </Button>
                )}
              </Card.Footer>
            </Card>
          ))}
        </div>
      ))}
    </div>
  );
}
