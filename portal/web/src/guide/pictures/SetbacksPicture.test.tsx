import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { WORDS } from "../words";
import { PICTURES } from ".";
import { SetbacksPicture } from "./SetbacksPicture";

test("the setbacks picture names each lot line with the drawing's approved words, and no distance", () => {
  const { container } = render(<GuideTheme><SetbacksPicture /></GuideTheme>);
  const texts = [...container.querySelectorAll("text")].map((t) => t.textContent);
  const rows = WORDS.drawing.rows;
  expect([...texts].sort()).toEqual([rows.front, rows.side_1, rows.side_2, rows.rear].sort());
  expect(texts.join(" ")).not.toMatch(/\d/);
});

test("an entry can name it", () => expect(PICTURES.setbacks).toBe(SetbacksPicture));
