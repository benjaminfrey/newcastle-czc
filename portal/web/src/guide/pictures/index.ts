import type { JSX } from "react";
import { SetbacksPicture } from "./SetbacksPicture";
import { StoriesPicture } from "./StoriesPicture";

// A library entry names its picture by id (the library's `picture`); these are the pictures there are.
export const PICTURES: Record<string, () => JSX.Element> = {
  stories: StoriesPicture,
  setbacks: SetbacksPicture,
};
