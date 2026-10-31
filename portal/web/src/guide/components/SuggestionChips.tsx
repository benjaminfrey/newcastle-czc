import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import type { ReactElement } from "react";

// Short suggestions the person can tap instead of typing.
export function SuggestionChips({ chips, onChip }: {
  chips: { id: string; label: string; icon?: ReactElement }[]; onChip: (id: string) => void;
}) {
  return (
    <Stack direction="row" useFlexGap sx={{ flexWrap: "wrap", gap: 1 }}>
      {chips.map((c) => (
        <Chip key={c.id} label={c.label} icon={c.icon} variant="outlined" clickable onClick={() => onChip(c.id)} />
      ))}
    </Stack>
  );
}
