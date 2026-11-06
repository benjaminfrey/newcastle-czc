import type { JSX } from "react";
import { StoriesPicture } from "./StoriesPicture";

// A library entry names its picture by id (entries.yaml `picture`); these are the pictures there are.
export const PICTURES: Record<string, () => JSX.Element> = {
  stories: StoriesPicture,
};
