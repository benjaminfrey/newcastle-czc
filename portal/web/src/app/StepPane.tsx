import type { FormSection } from "../applications";
import type { Row } from "../forms/applicability";
import InsetGroup from "../shell/InsetGroup";
import { useRowControls } from "./WizardPane";

// A step's questions as grouped lists, one per section of the official form: what review's Edit
// sheet shows until review links to the wizard's screens (wizard Task 6).
export default function StepPane({ rows, sections }: { rows: Row[]; sections: FormSection[] }) {
  const control = useRowControls();
  return (
    <>
      {sections.map((s) => {
        const mine = rows.filter((r) => r.section.id === s.id);
        if (mine.length === 0) return null;
        return <InsetGroup key={s.id} title={s.official_title}>{mine.map((r) => control(r))}</InsetGroup>;
      })}
    </>
  );
}
