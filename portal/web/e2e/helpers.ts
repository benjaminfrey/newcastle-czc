import AxeBuilder from "@axe-core/playwright";
import { expect, type Locator, type Page } from "@playwright/test";

const MAILPIT = process.env.PORTAL_E2E_MAILPIT ?? "http://127.0.0.1:8025";
// The LAN stack's Mailpit asks for a login ("user:password", as MAILPIT_UI_AUTH in .env).
const MAILPIT_AUTH = process.env.PORTAL_E2E_MAILPIT_AUTH;
const mailpit = (path: string) => fetch(`${MAILPIT}${path}`, MAILPIT_AUTH
  ? { headers: { Authorization: `Basic ${Buffer.from(MAILPIT_AUTH).toString("base64")}` } } : undefined);
const checked = new Set<string>();

// Fails on serious or critical accessibility findings; each kind of page is checked once per run.
export async function axe(page: Page, name: string) {
  const key = `${name}:${await page.evaluate(() => document.documentElement.dataset.theme ?? "light")}`;
  if (checked.has(key)) return;
  checked.add(key);
  // Colours are only true once a sheet or pane has finished fading in.
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"), null, { timeout: 5000 }).catch(() => {});
  const results = await new AxeBuilder({ page }).exclude(".maplibregl-canvas").analyze();
  const bad = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad.map((v) => `${v.id}: ${v.help} — ${v.nodes.map((n) => `${n.target.join(" ")} ${n.html.slice(0, 120)} ${n.any?.[0]?.message ?? ""}`).join(" | ")}`),
         `axe on ${key}`).toEqual([]);
}

export function newEmail(tag: string): string {
  return `e2e-${tag}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

async function linkFor(email: string): Promise<string> {
  for (let i = 0; i < 30; i += 1) {
    const r = await mailpit(`/api/v1/search?query=${encodeURIComponent(`to:"${email}"`)}`);
    const found = (await r.json()) as { messages: { ID: string }[] };
    if (found.messages?.length) {
      const m = (await (await mailpit(`/api/v1/message/${found.messages[0].ID}`)).json()) as { Text: string };
      const link = m.Text.match(/https?:\/\/\S+\/signin\/verify#token=[\w-]+/);
      if (link) return link[0];
    }
    await new Promise((res) => setTimeout(res, 500));
  }
  throw new Error(`no sign-in email for ${email}`);
}

// Wherever the sign-in form shows (its page, or the sheet on "What you'll need"): ask for a
// link, read it from Mailpit, follow it, press the button.
export async function signInHere(page: Page, email: string) {
  await page.getByLabel("Your email address").fill(email);
  await page.getByRole("button", { name: "Email me a sign-in link" }).click();
  await expect(page.getByText("Check your email")).toBeVisible();
  const link = await linkFor(email);
  await page.goto(new URL(link).pathname + new URL(link).hash);
  await page.getByRole("button", { name: "Sign me in" }).click();
}

export type Project = "use" | "build" | "driveway";

const settle = (page: Page) =>
  page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"), null, { timeout: 5000 }).catch(() => {});
const next = (page: Page) => page.getByRole("button", { name: /^(Continue|Skip for now)$/ });

// "Do I need a permit?", one question at a time: what you're planning, the kind of building work
// and its size, the property, what you'll need, then Start and the sign-in screen.
export async function screenerToStart(page: Page, project: Project, application: string, email: string) {
  await page.goto("/start");
  const choice = { use: /Start a business/, build: /Build something new/, driveway: /driveway/ }[project];
  await page.getByRole("checkbox", { name: choice }).click();
  await axe(page, "start: choose several");
  await next(page).click();
  if (project === "build") {
    await page.getByRole("radio", { name: "A new building" }).click();
    await page.getByRole("textbox", { name: /floor area/i }).fill("1200");
    await axe(page, "start: a number");
    await next(page).click();
    await next(page).click(); // new homes: skip for now
    await next(page).click(); // homes in the last five years: skip for now
  }
  await page.getByLabel("Street address, or map and lot").fill("4-36");
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("list", { name: "Search results" }).getByRole("button").first().click();
  await expect(page.getByRole("heading", { name: "Is this your property?" })).toBeVisible();
  await axe(page, "property");
  await page.getByRole("radio", { name: "Yes, this is my property" }).click();
  if (project === "use") {
    // Lot 4-36 is in D1, where a Farm/Vendor Market takes a Use Permit.
    await page.getByLabel("Search uses").fill("vendor market");
    await page.getByRole("button", { name: /^Choose Farm/ }).first().click();
  }
  await expect(page.getByRole("heading", { level: 2, name: /^You('ll| may) need/ }).first()).toBeVisible();
  await axe(page, "needs");
  await page.getByRole("button", { name: `Start this application: ${application}` }).click();
  await expect(page.getByRole("heading", { name: "Sign in to apply" })).toBeVisible();
  await axe(page, "sign-in screen");
  await signInHere(page, email);
  // A new application opens at its first card, on a desktop and a phone alike; the task list is
  // a tap away (‹ Tasks on a phone, the sidebar on a desktop). Open it and come back, as a person
  // checking would.
  await expect(page).toHaveURL(/\/applications\/[0-9a-f-]+\/[a-z_]+/);
  await axe(page, "first card");
  if ((page.viewportSize()?.width ?? 1280) < 1024) {
    await page.getByRole("link", { name: "Tasks" }).click();
    await expect(page).toHaveURL(/\/applications\/[0-9a-f-]+$/);
    await axe(page, "task list");
    await page.getByRole("link", { name: /, Not started$/ }).first().click();
    await expect(page).toHaveURL(/\/applications\/[0-9a-f-]+\/[a-z_]+/);
  }
}

const ANSWERS: [RegExp, string][] = [
  [/full name|owner's full name|their name/i, "Test Applicant"],
  [/phone/i, "207-555-0100"],
  [/email/i, "someone@example.com"],
];

// Fill every unanswered typed control inside `scope`: text, long text, numbers, sliders, the roof
// slope picker, uses, uploads and the map pin.
export async function fillControls(page: Page, scope: Locator, fixture: string) {
  // Uses first: a chosen use can open a follow-up question below it.
  for (const row of await scope.locator("[data-field]").filter({ has: page.getByRole("button", { name: "Add a use" }) }).all()) {
    if (await row.getByRole("row").count()) continue;
    await row.getByRole("button", { name: "Add a use" }).click();
    const sheet = page.getByRole("dialog", { name: "Add a use" });
    await sheet.getByLabel("Search uses").fill("office");
    await sheet.getByRole("button", { name: /^Add Office/ }).first().click();
    await expect(sheet).toBeHidden();
  }
  for (const box of await scope.locator('input[type="text"]:not([inputmode]), input[type="email"], input[type="tel"], input:not([type])').all()) {
    if (!(await box.isVisible()) || (await box.inputValue()) || (await box.getAttribute("role")) === "searchbox") continue;
    const label = (await box.getAttribute("aria-label")) ?? (await box.evaluate((el) => (el as HTMLInputElement).labels?.[0]?.textContent ?? ""));
    if (/^Search/.test(label)) continue;
    await box.fill(ANSWERS.find(([r]) => r.test(label))?.[1] ?? "Test answer");
    await box.blur();
  }
  for (const area of await scope.locator("textarea").all()) {
    if ((await area.isVisible()) && !(await area.inputValue())) { await area.fill("A short test description."); await area.blur(); }
  }
  for (const num of await scope.locator('input[inputmode="decimal"], input[inputmode="numeric"]').all()) {
    if (!(await num.isVisible()) || (await num.inputValue())) continue;
    await num.fill("12"); await num.blur();
  }
  // A count with − and + (floors above ground): one, if it's blank.
  for (const more of await scope.getByRole("button", { name: /, one more$/ }).all()) {
    if ((await more.locator("xpath=preceding-sibling::span[1]").textContent())?.trim() === "–") await more.click();
  }
  for (const slider of await scope.getByRole("slider").all()) {
    await slider.focus(); await page.keyboard.press("ArrowRight");
  }
  for (const picker of await scope.locator('button[aria-haspopup="listbox"]').all()) {
    if (!(await picker.isVisible()) || !/Choose…/.test((await picker.textContent()) ?? "")) continue;
    await picker.click();
    await page.getByRole("option").first().click();
  }
  for (const file of await scope.locator('input[type="file"]').all()) {
    await file.setInputFiles(fixture);
    await expect(scope.getByRole("list", { name: "Files added" }).first()).toBeVisible({ timeout: 60_000 });
  }
  const map = scope.getByRole("region", { name: "Map of Newcastle" });
  if (await map.count()) {
    // MapLibre drops clicks until its style has loaded and the lot is framed.
    for (let tries = 0; tries < 4; tries += 1) {
      await map.first().scrollIntoViewIfNeeded();
      await page.waitForTimeout(1500);
      const box = await map.first().boundingBox();
      await page.mouse.click(box!.x + box!.width / 2, box!.y + box!.height / 2);
      if (await scope.getByText(/^Marked\./).isVisible().catch(() => false)) break;
    }
    await expect(scope.getByText(/^Marked\./)).toBeVisible();
  }
}

type Plan = { extraBuilding?: boolean; copyBuilding?: boolean; component?: boolean };

const appPath = /^\/applications\/[0-9a-f-]+$/;

// Answer the card that is showing, the way a person would: "Yes, that's right" for a map value;
// a tap on a card with no Continue; else the first choice in each group (No, where a group has
// one), values for typed questions, then Continue.
export async function answerScreen(page: Page, fixture: string) {
  await settle(page);
  const pane = page.locator("[data-card-body]").first();
  const right = pane.getByRole("radio", { name: "Yes, that's right" });
  if (await right.count()) {
    await axe(page, "card: is this right");
    return right.click();
  }
  const pick = async (group: Locator) => {
    const no = group.getByRole("radio", { name: "No", exact: true });
    await ((await no.count()) ? no : group.getByRole("radio").first()).click();
  };
  const groups = pane.getByRole("radiogroup");
  if ((await groups.count()) && !(await next(page).count())) {
    await axe(page, "card: one choice");
    return pick(groups.first()); // a tap answers and moves on
  }
  // A choice can bring the next one (the roof's shape, then its slope): answer until none is left.
  for (let round = 0; round < 4; round += 1) {
    const open = [];
    for (const g of await groups.all()) if (!(await g.locator('[aria-checked="true"]').count())) open.push(g);
    if (!open.length) break;
    for (const g of open) await pick(g);
  }
  const several = pane.getByRole("checkbox");
  if ((await several.count()) && !(await pane.locator('[role="checkbox"][aria-checked="true"]').count())) {
    await axe(page, "card: choose several");
    await several.first().click();
  }
  await fillControls(page, pane, fixture);
  await axe(page, `card: ${(await pane.getByRole("slider").count()) ? "walls" : (await pane.locator('input[type="file"]').count()) ? "upload" : "typed"}`);
  await next(page).click();
}

// Every task of the application, from the task list, until Check and send: each task's cards, its
// check page, and for buildings and additions the list (one more building, a copy, or an
// addition, when the plan asks).
export async function completeApplication(page: Page, fixture: string, plan: Plan = {}) {
  for (let i = 0; i < 200; i += 1) {
    await settle(page);
    const path = new URL(page.url()).pathname;
    if (/\/review$/.test(path)) return;
    const before = page.url();
    const main = page.getByRole("main");
    if (appPath.test(path)) {
      await axe(page, "task list");
      const send = main.getByRole("link", { name: "Check and send" });
      await ((await send.count()) ? send : main.getByRole("link", { name: /, (Not started|\d+ of \d+ answered)$/ }).first()).click();
    } else if (/\/check$/.test(path)) {
      await axe(page, "check page");
      await page.getByRole("button", { name: "Done" }).click();
    } else if (await page.getByRole("button", { name: /^(Done with|No) (buildings|additions)$/ }).count()) {
      await axe(page, "items list");
      const finish = page.getByRole("button", { name: /^Finish / });
      if (await finish.count()) await finish.first().click();
      else if (plan.copyBuilding && (await page.getByRole("button", { name: /^Copy Building/ }).count())) {
        plan.copyBuilding = false;
        await page.getByRole("button", { name: /^Copy Building/ }).click();
      } else if (plan.extraBuilding && (await page.getByRole("button", { name: "Add a building" }).count())) {
        plan.extraBuilding = false;
        await page.getByRole("button", { name: "Add a building" }).click();
      } else if (plan.component && (await page.getByRole("button", { name: "Add an addition, porch or deck" }).count())) {
        plan.component = false;
        await page.getByRole("button", { name: "Add an addition, porch or deck" }).click();
      } else await page.getByRole("button", { name: /^(Done with|No) (buildings|additions)$/ }).click();
    } else {
      await answerScreen(page, fixture);
    }
    await expect(page, `stuck on ${before}`).not.toHaveURL(before, { timeout: 10_000 });
  }
  throw new Error("didn't reach Check and send in 200 screens");
}

// On Check and send: every field is filled or marked, and nothing is still to answer.
export async function expectReviewComplete(page: Page, title: string) {
  await expect(page.getByRole("main").getByText("Check and send").first()).toBeVisible();
  await expect(page.getByText(title).first()).toBeVisible();
  await axe(page, "review");
  await expect(page.getByRole("group", { name: "Still to answer" })).toHaveCount(0);
  await expect(page.getByText("Still to answer")).toHaveCount(0);
}

// The task list's tasks, by name (the sidebar on a desktop, the home screen on a phone).
export async function taskNames(page: Page): Promise<string[]> {
  const nav = page.getByRole("navigation", { name: "Tasks" });
  const scope = (await nav.count()) ? nav : page.getByRole("main");
  return (await scope.getByRole("link").allTextContents()).map((t) => t.trim());
}
