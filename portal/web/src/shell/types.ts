import type { ReactNode } from "react";
export type StepStatus = "todo" | "started" | "done";
export type SaveState = "idle" | "saving" | "saved" | "error" | "conflict";
export type ShellStep = {
  id: string; title: string; status: StepStatus; unknowns: number; href: string;
  children?: ShellStep[];
};
export type ShellActions = {
  back?: () => void;
  continueLabel?: string;
  onContinue?: () => void;
  dots?: ReactNode; // where you are in the section, at the bottom left
};
