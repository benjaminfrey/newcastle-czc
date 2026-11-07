import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as api from "../api";
import { RECT } from "./fixtures";
import { useDrawing } from "./useDrawing";

vi.mock("../api", async (orig) => ({ ...(await orig<typeof import("../api")>()), getDrawing: vi.fn() }));
const getDrawing = vi.mocked(api.getDrawing);

beforeEach(() => getDrawing.mockReset());

test("it fetches the drawing, and again when the revision changes", async () => {
  getDrawing.mockResolvedValue(RECT);
  const { result, rerender } = renderHook(({ rev }) => useDrawing("p1", rev), { initialProps: { rev: 3 } });
  await waitFor(() => expect(result.current).toEqual(RECT));
  rerender({ rev: 4 });
  await waitFor(() => expect(getDrawing).toHaveBeenCalledTimes(2));
});

test("no outline, a refusal or no revision gives no drawing", async () => {
  getDrawing.mockResolvedValue({ ...RECT, outline: null });
  const a = renderHook(() => useDrawing("p1", 1));
  await waitFor(() => expect(getDrawing).toHaveBeenCalled());
  expect(a.result.current).toBeNull();
  getDrawing.mockResolvedValue("unavailable");
  const b = renderHook(() => useDrawing("p1", 2));
  await waitFor(() => expect(getDrawing).toHaveBeenCalledTimes(2));
  expect(b.result.current).toBeNull();
  renderHook(() => useDrawing("p1", undefined));
  expect(getDrawing).toHaveBeenCalledTimes(2);
});

test("the last drawing stays while the next one loads", async () => {
  getDrawing.mockResolvedValueOnce(RECT).mockReturnValueOnce(new Promise(() => {}));
  const { result, rerender } = renderHook(({ rev }) => useDrawing("p1", rev), { initialProps: { rev: 1 } });
  await waitFor(() => expect(result.current).toEqual(RECT));
  rerender({ rev: 2 });
  expect(result.current).toEqual(RECT);
});
