import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import { clearUseGroupsCache } from "./api";
import { clearFormCache } from "./projects";

afterEach(() => {
  cleanup();
  clearUseGroupsCache();
  clearFormCache();
  vi.restoreAllMocks();
});
