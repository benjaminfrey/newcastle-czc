import { useSyncExternalStore } from "react";

// Desktop and tablet (≥ 1024 px) get the two-pane window; narrower screens the phone stack.
const QUERY = "(min-width: 1024px)";

function subscribe(onChange: () => void): () => void {
  if (typeof matchMedia !== "function") return () => {};
  const mql = matchMedia(QUERY);
  mql.addEventListener("change", onChange);
  return () => mql.removeEventListener("change", onChange);
}

export function useWideLayout(): boolean {
  return useSyncExternalStore(subscribe, () => typeof matchMedia === "function" && matchMedia(QUERY).matches, () => true);
}
