import { useEffect, useState } from "react";
import { getDrawing, type Drawing } from "../api";

/** The lot drawing for a project, fetched again at each new revision (the front can change).
 *  Null while the first one loads, on a refusal, or when the lot has no outline. */
export function useDrawing(projectId: string, revision: number | undefined): Drawing | null {
  const [drawing, setDrawing] = useState<Drawing | null>(null);
  useEffect(() => {
    if (revision === undefined) return;
    let live = true;
    void getDrawing(projectId).then((d) => {
      if (!live) return;
      setDrawing(typeof d === "object" && "outline" in d && d.outline ? d : null);
    });
    return () => { live = false; };
  }, [projectId, revision]);
  return drawing;
}
