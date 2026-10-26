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


const settle = (page: Page) =>
  page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"), null, { timeout: 5000 }).catch(() => {});
const next = (page: Page) => page.getByRole("button", { name: /^(Continue|Skip for now)$/ });

// Sign in first (projects brief §3): Home's sign-in card, the emailed link; then Start a new
// application and its three cards — how to reach you, the lot (4-36), the parts — and Go to my
// project, which opens the dashboard.
export async function startProject(page: Page, parts: RegExp[], email: string) {
  await page.goto("/");
  await axe(page, "home signed out");
  await signInHere(page, email);
  await expect(page.getByRole("link", { name: "Start a new application" })).toBeVisible();
  await axe(page, "home");
  await page.getByRole("link", { name: "Start a new application" }).click();
  await expect(page.getByRole("heading", { name: "How can the Town reach you?" })).toBeVisible();
  await axe(page, "start: reach you");
  await page.getByLabel("Full name").fill("Test Applicant");
  await page.getByLabel("Phone").fill("207-555-0100");
  await page.getByLabel("Mailing address").fill("PO Box 1, Newcastle ME 04553");
  await next(page).click();
  await page.getByLabel("Street address, or map and lot").fill("4-36");
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("list", { name: "Search results" }).getByRole("button").first().click();
  await expect(page.getByRole("heading", { name: "Is this your property?" })).toBeVisible();
  await axe(page, "start: property");
  await page.getByRole("radio", { name: "Yes, this is my property" }).click();
  await expect(page.getByRole("heading", { name: "What are you doing here?" })).toBeVisible();
  for (const p of parts) await page.getByRole("checkbox", { name: p }).click();
  await axe(page, "start: parts");
  await page.getByRole("button", { name: "Go to my project" }).click();
  await expect(page).toHaveURL(projectPath);
  await expect(page.getByRole("list", { name: "Your project" })).toBeVisible();
  await axe(page, "dashboard");
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
    if (!(await more.locator("xpath=preceding-sibling::span[1]").textContent())?.trim()) await more.click();
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

const projectPath = /\/projects\/[0-9a-f-]+$/;

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

// Every row of the project, from the dashboard, until Check and send: each row's cards, its check
// page, and for buildings and additions the list (one more building or a copy, when the plan asks).
export async function completeProject(page: Page, fixture: string, plan: Plan = {}) {
  for (let i = 0; i < 200; i += 1) {
    await settle(page);
    const path = new URL(page.url()).pathname;
    if (/\/send$/.test(path)) return;
    const before = page.url();
    const main = page.getByRole("main");
    if (projectPath.test(path)) {
      const open = main.getByRole("link", { name: /,\s*(Not started|\d+ of \d+\s*answered)$/ });
      await ((await open.count()) ? open.first() : main.getByRole("link", { name: "Check and send" })).click();
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
      } else await page.getByRole("button", { name: /^(Done with|No) (buildings|additions)$/ }).click();
    } else {
      await answerScreen(page, fixture);
    }
    await expect(page, `stuck on ${before}`).not.toHaveURL(before, { timeout: 10_000 });
  }
  throw new Error("didn't reach Check and send in 200 screens");
}

// On Check and send with nothing left: the project at a glance, the fees, the forms; then Send,
// its confirmation, and the dashboard's Sent.
export async function sendProject(page: Page, forms: string[]) {
  await expect(page.getByRole("region", { name: /to finish first$/ })).toHaveCount(0);
  for (const f of forms) await expect(page.getByRole("region", { name: "The official forms" })).toContainText(f);
  await axe(page, "check and send");
  await page.getByRole("button", { name: "Send to the Town" }).click();
  const sheet = page.getByRole("alertdialog");
  await expect(sheet.getByRole("heading", { name: "Send your project to the Town?" })).toBeVisible();
  await axe(page, "send: confirm");
  await sheet.getByRole("button", { name: "Send" }).click();
  await expect(page).toHaveURL(projectPath);
  await expect(page.getByText(/You can still add to your project until the Town locks it for review\./)).toBeVisible();
}
