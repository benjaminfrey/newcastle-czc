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
};
