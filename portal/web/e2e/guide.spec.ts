import { expect, test, type Page } from "@playwright/test";
import { axe, newEmail, startProject } from "./helpers";

// The guided conversation (guided plan 3) on the LAN copy, built with VITE_GUIDE_PREVIEW=1 and
// allowing draft wording. Lot 4-36 is in D1 (Rural), where 15 ft is the side setback minimum.

const turn = (page: Page) => page.locator("main section[data-turn]");
const question = (page: Page) => page.getByRole("main").getByRole("heading", { level: 2 }).first();

async function choose(page: Page, label: string) {
  await turn(page).getByText(label, { exact: true }).click();
}

// The opening scene's list (guided plan 5): the keyboard's and the tests' way in.
async function pickFromList(page: Page, label: string) {
  await page.getByRole("list", { name: "Or choose from the list" }).getByRole("button", { name: label, exact: true }).click();
}

async function number(page: Page, ask: RegExp, value: string) {
  await expect(question(page)).toHaveText(ask);
  await turn(page).getByRole("textbox").fill(value);
  await turn(page).getByRole("button", { name: "Next" }).click();
  await expect(question(page)).not.toHaveText(ask);
}

// Sign in, start a building project on 4-36, and open its guide at the opening.
async function openGuide(page: Page, tag: string) {
  await startProject(page, [/^A new building/], newEmail(tag));
  await page.getByRole("link", { name: "Try the guided version (preview)" }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+\/guide$/);
  await expect(question(page)).toHaveText("What would you like to do?");
  await pickFromList(page, "A new house");
  await expect(question(page)).toHaveText(/what the Town knows about your lot/);
}

// The lot's outline is on the tax map, so after the lot the guide asks which line is the front.
async function chooseFront(page: Page) {
  await expect(question(page)).toHaveText("Which lot line is the front?");
  await axe(page, "guide: the front line");
  await turn(page).getByText(/^The line along /).first().click();
}

async function toTheBuilding(page: Page) {
  await axe(page, "guide: the lot");
  await choose(page, "Yes, that's right");
  await chooseFront(page);
  await expect(question(page)).toHaveText(/^So you'd like to build a new house/);
  await choose(page, "Yes, that's right");
  await number(page, /full stories/, "2");
  await number(page, /inside the roof/, "0");
  await expect(question(page)).toHaveText(/basement wall/);
  await choose(page, "No, or there's no basement");
}

async function toTheSetbacks(page: Page) {
  await toTheBuilding(page);
  await number(page, /floor area/, "1,800");   // no standard of its own: the Town's form asks it
  await number(page, /How many homes/, "1");
  await number(page, /front lot line/, "30");
}

test("a new house that fits reaches Check and send", async ({ page }, info) => {
  await openGuide(page, `guide-ready-${info.project.name}`);
  await toTheSetbacks(page);
  await expect(question(page)).toHaveText(/nearest side lot line/);
  await turn(page).getByRole("textbox").fill("20");
  await expect(turn(page).getByRole("status")).toHaveText("Within the limit · 5 ft to spare");
  await expect(turn(page).getByRole("slider")).toBeVisible();
  await axe(page, "guide: a number");
  await turn(page).getByRole("button", { name: "Next" }).click();
  await number(page, /other side lot line/, "20");
  await turn(page).getByRole("textbox").fill("20");
  await turn(page).getByRole("button", { name: "Next" }).click();
  await expect(question(page)).toHaveText("Your application is ready to send");
  await expect(page.getByRole("main")).toContainText("Small Project Plan");
  await axe(page, "guide: ready");
  await page.getByRole("link", { name: "Check and send" }).click();
  await expect(question(page)).toHaveText("Check your project");
  await expect(page.getByRole("main")).toContainText("1,800 sq ft");
  await axe(page, "guide: check and send");
  // The official form still has questions the guide doesn't ask (who owns the lot and so on),
  // so Send lists them instead of sending.
  await page.getByRole("button", { name: "Send to the Town" }).click();
  await expect(page.getByText("Before you send, the Town's form still needs:")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
});

test("a side setback that doesn't fit offers the nearest", async ({ page }, info) => {
  await openGuide(page, `guide-fit-${info.project.name}`);
  await toTheSetbacks(page);
  await expect(question(page)).toHaveText(/nearest side lot line/);
  await turn(page).getByRole("textbox").fill("11");
  await expect(turn(page).getByRole("status")).toHaveText("4 ft short of the limit here");
  await turn(page).getByRole("button", { name: "Next" }).click();
  await expect(question(page)).toHaveText(/That's 4 ft short of the limit here/);
  await expect(page.getByRole("main")).not.toContainText("How many homes");   // its own page
  await axe(page, "guide: doesn't fit");
  await choose(page, "Make it 15 ft");
  await expect(question(page)).toHaveText(/other side lot line/);
  if (info.project.name === "phone") await page.getByRole("button", { name: "Your project" }).click();
  const panel = info.project.name === "phone" ? page.getByRole("dialog") : page.getByRole("complementary", { name: "Your project" });
  await expect(panel.getByRole("group", { name: "Where it sits" })).toContainText("15 ft");
  await expect(panel.getByRole("group", { name: "Where it sits" })).toContainText("Fits");
});

test("the guide picks up where it left off", async ({ page }, info) => {
  await openGuide(page, `guide-reload-${info.project.name}`);
  await toTheBuilding(page);
  await expect(question(page)).toHaveText(/floor area/);
  const step = await page.getByRole("progressbar").getAttribute("aria-valuenow");
  await page.reload();
  await expect(question(page)).toHaveText(/floor area/);
  await expect(page.getByRole("main")).toContainText("No, or there's no basement");
  expect(await page.getByRole("progressbar").getAttribute("aria-valuenow")).toBe(step);
});

test("Change keeps what still applies", async ({ page }, info) => {
  await openGuide(page, `guide-change-${info.project.name}`);
  await toTheSetbacks(page);
  await expect(question(page)).toHaveText(/nearest side lot line/);
  if (info.project.name === "phone") await page.getByRole("button", { name: "Your project" }).click();
  await page.getByRole("button", { name: /^Change: What is the floor area/ }).click();
  await number(page, /floor area/, "2,000");
  // Everything after it still stands, so the guide goes straight back to the next open question.
  await expect(question(page)).toHaveText(/nearest side lot line/);
});

test("No on So you mean starts again from a picture", async ({ page }, info) => {
  await openGuide(page, `guide-no-${info.project.name}`);
  await choose(page, "Yes, that's right");
  await chooseFront(page);
  await expect(question(page)).toHaveText(/^So you'd like to build a new house/);
  await choose(page, "No, something else");
  await expect(question(page)).toHaveText("What would you like to do?");
  await pickFromList(page, "A new house");
  await expect(question(page)).toHaveText(/what the Town knows about your lot/);
});

test("Back after a Change puts that answer back", async ({ page }, info) => {
  await openGuide(page, `guide-change-back-${info.project.name}`);
  await toTheSetbacks(page);
  await expect(question(page)).toHaveText(/nearest side lot line/);
  if (info.project.name === "phone") await page.getByRole("button", { name: "Your project" }).click();
  await page.getByRole("button", { name: /^Change: What is the floor area/ }).click();
  await expect(question(page)).toHaveText(/floor area/);
  await page.getByRole("button", { name: "Back to the last question" }).click();
  await expect(question(page)).toHaveText(/nearest side lot line/);
  await expect(page.getByRole("main")).toContainText("1,800 sq ft");
});

test("on a phone, your project opens from the app bar", async ({ page }, info) => {
  test.skip(info.project.name !== "phone", "phone only");
  await openGuide(page, `guide-phone-${info.project.name}`);
  await toTheBuilding(page);
  await page.getByRole("button", { name: "Your project" }).click();
  const sheet = page.getByRole("dialog");
  await expect(sheet.getByRole("group", { name: "The building" })).toContainText("2");
  await axe(page, "guide: your project on a phone");
  await sheet.getByRole("button", { name: "Close" }).click();
  await expect(sheet).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
});

// --- plan 4: the lot drawing ---

const drawing = (page: Page) => page.getByRole("img", { name: /A drawing of your lot/ });

test("the drawing shows the lot and the setbacks", async ({ page }, info) => {
  await openGuide(page, `guide-drawing-${info.project.name}`);
  await toTheSetbacks(page);
  await expect(question(page)).toHaveText(/nearest side lot line/);
  if (info.project.name === "phone") {
    await expect(turn(page).getByRole("img", { name: /A drawing of your lot/ })).toBeVisible();
  } else {
    await expect(page.getByRole("complementary", { name: "Your project" }).getByRole("img", { name: /A drawing of your lot/ })).toBeVisible();
  }
  await expect(page.getByText("Approximate: from the Town's tax map, not a survey").first()).toBeVisible();
  const list = page.getByRole("group", { name: "The setbacks on your lot" }).first();
  await expect(list).toContainText("Nearest side");
  await expect(list).toContainText("At least 15 ft");
  await axe(page, "guide: the drawing");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
});

test("dragging the side edge fills the field", async ({ page }, info) => {
  test.skip(info.project.name === "phone", "desktop: a mouse drag");
  await openGuide(page, `guide-drag-${info.project.name}`);
  await toTheSetbacks(page);
  await expect(question(page)).toHaveText(/nearest side lot line/);
  const handle = drawing(page).locator("[data-handle='side_1']");
  const box = (await handle.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 30, box.y + box.height / 2, { steps: 5 });
  await page.mouse.up();
  const field = turn(page).getByRole("textbox");
  await expect(field).toHaveValue(/^\d+$/);
  await turn(page).getByRole("button", { name: "Next" }).click();
  await expect(question(page)).not.toHaveText(/nearest side lot line/);
});


// Plan 5: the scene on a project with only a use. Tapping the house adds a building and starts;
// the deck says coming soon; every pin's target is 48 px and inside the picture; the stories
// explanation shows its cut-away.
test("the opening scene: coming soon, add to the project, and the stories picture", async ({ page }, info) => {
  await startProject(page, [/^Start or change a use/], newEmail(`guide-scene-${info.project.name}`));
  await page.getByRole("link", { name: "Try the guided version (preview)" }).click();
  const scene = page.getByRole("img", { name: /^A Newcastle lot/ });
  await expect(scene).toBeVisible();
  await axe(page, "guide: the opening scene");

  const box = await scene.boundingBox();
  for (const hit of await page.locator("svg[role=img] circle[data-hit]").all()) {
    const b = (await hit.boundingBox())!;
    expect(b.width).toBeGreaterThanOrEqual(47.5);
    expect(b.x + b.width / 2).toBeGreaterThanOrEqual(box!.x);
    expect(b.x + b.width / 2).toBeLessThanOrEqual(box!.x + box!.width);
  }

  await page.locator('circle[data-hit][data-for="deck"]').click();
  const soon = page.getByRole("dialog", { name: "A deck: coming soon" });
  await expect(soon).toBeVisible();
  await axe(page, "guide: coming soon");
  await soon.getByRole("button", { name: "OK" }).click();
  await expect(soon).toBeHidden();

  await page.locator('circle[data-hit][data-for="house_outline"]').click();
  const add = page.getByRole("dialog", { name: "Add a new house to this project?" });
  await expect(add).toBeVisible();
  await add.getByRole("button", { name: "Add it" }).click();
  await expect(question(page)).toHaveText(/what the Town knows about your lot/);
  await choose(page, "Yes, that's right");
  await chooseFront(page);
  await choose(page, "Yes, that's right");
  await expect(question(page)).toHaveText(/full stories/);
  await expect(page.getByRole("img", { name: /^A house cut open to show its floors/ })).toBeVisible();
  await axe(page, "guide: the stories picture");
});
