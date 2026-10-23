import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

const MAILPIT = process.env.PORTAL_E2E_MAILPIT ?? "http://127.0.0.1:8025";
// The LAN stack's Mailpit asks for a login ("user:password", as MAILPIT_UI_AUTH in .env).
const MAILPIT_AUTH = process.env.PORTAL_E2E_MAILPIT_AUTH;
const mailpit = (path: string) => fetch(`${MAILPIT}${path}`, MAILPIT_AUTH
  ? { headers: { Authorization: `Basic ${Buffer.from(MAILPIT_AUTH).toString("base64")}` } } : undefined);
const checked = new Set<string>();

// Fails on serious or critical accessibility findings; each kind of page is checked once per run.
export async function axe(page: Page, name: string) {
  if (checked.has(name)) return;
  checked.add(name);
  const results = await new AxeBuilder({ page }).exclude(".maplibregl-canvas").analyze();
  const bad = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad.map((v) => `${v.id}: ${v.help} — ${v.nodes.map((n) => `${n.target.join(" ")} ${n.html.slice(0, 120)} ${n.any?.[0]?.message ?? ""}`).join(" | ")}`), `axe on ${name}`).toEqual([]);
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

// On the sign-in page: ask for a link, read it from Mailpit, follow it, press the button.
export async function signInHere(page: Page, email: string) {
  await expect(page).toHaveURL(/\/signin$/);
  await page.getByLabel(/email/i).fill(email);
  await page.getByRole("button", { name: /send|link/i }).click();
  const link = await linkFor(email);
  await page.goto(new URL(link).pathname + new URL(link).hash);
  await page.getByRole("button", { name: "Sign me in" }).click();
}

export type Project = "use" | "build" | "driveway";

// "Do I need a permit?" → "Where is it?" → results → Start.
export async function screenerToStart(page: Page, project: Project, startName: RegExp) {
  await page.goto("/start");
  const choice = { use: /Start a business/, build: /Build something new/, driveway: /driveway/ }[project];
  await page.getByRole("checkbox", { name: choice }).check({ force: true });
  if (project === "build") {
    await page.getByRole("radio", { name: "A new building" }).check({ force: true });
    await page.getByRole("textbox", { name: /floor area/i }).first().fill("1200");
  }
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel("Street address, or map and lot").fill("4-36");
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("list", { name: "Search results" }).getByRole("button").first().click();
  await axe(page, "where");
  await page.getByRole("button", { name: "Yes, this is my property" }).click();
  if (project === "use") {
    // Lot 4-36 is in D1, where a Farm/Vendor Market takes a Use Permit.
    await page.getByLabel("Search uses").fill("vendor market");
    await page.getByRole("button", { name: /^Choose Farm/ }).first().click();
  }
  await expect(page.getByRole("heading", { name: "Here's what you'll need" })).toBeVisible();
  await axe(page, "results");
  await page.getByRole("link", { name: startName }).click();
}

type Plan = { adds: Record<string, number>; unknownOnce: boolean };

const RADIO: [RegExp, string][] = [
  [/Do you own the property/, "Yes"],
  [/Should the Town also contact/, "No"],
  [/neighboring lot share/, "No"],
  [/only being renovated/, "No"],
  [/What are you adding or changing/, "A deck"],
  [/MaineDOT entrance permit/, "Not yet"],
  [/traffic light/, "No"],
  [/ditch/, "No"],
];

// Answer whatever question is on screen; returns false once the review page is reached.
export async function answerScreen(page: Page, plan: Plan, fixture: string): Promise<boolean> {
  if (/\/review/.test(page.url())) return false;
  const h1 = page.getByRole("heading", { level: 1 });
  try {
    await h1.waitFor({ timeout: 10_000 });
  } catch {
    if (/\/review/.test(page.url())) return false;
    throw new Error(`no page heading at ${page.url()}: ${(await page.locator("main").textContent())?.slice(0, 400)}`);
  }
  if (/\/review/.test(page.url())) return false;
  const chapter = (await h1.textContent()) ?? "";
  await axe(page, `wizard:${chapter}`);
  const add = page.getByRole("button", { name: "Yes, add one" });
  if (await add.isVisible()) {
    const title = (await page.locator("text=/\\?$/").first().textContent()) ?? "";
    const kind = /building/i.test(title) ? "building" : "component";
    if ((plan.adds[kind] ?? 0) > 0) {
      plan.adds[kind] -= 1;
      await add.click();
    } else {
      await page.getByRole("button", { name: "No, go on" }).click();
    }
    await page.waitForTimeout(150);
    return true;
  }
  const unknown = page.getByRole("button", { name: "I don't know yet" });
  if (plan.unknownOnce && (await unknown.isVisible())) {
    plan.unknownOnce = false;
    await unknown.click();
    await page.waitForTimeout(150);
    return true;
  }
  const card = page.locator("main");
  const radios = card.getByRole("radio");
  const file = card.locator('input[type="file"]');
  const textarea = card.locator("textarea");
  const text = card.locator('input:not([type="file"]):not([type="radio"]):not([type="checkbox"])');
  const checkboxes = card.getByRole("checkbox");
  if (await card.getByRole("region", { name: "Map of Newcastle" }).isVisible().catch(() => false)) {
    const box = await card.getByRole("region", { name: "Map of Newcastle" }).boundingBox();
    await page.mouse.click(box!.x + box!.width / 2, box!.y + box!.height / 2);
    await expect(card.getByText(/^Marked/)).toBeVisible();
  } else if (await card.getByLabel("Search uses").isVisible().catch(() => false)) {
    if (!(await card.getByRole("list", { name: "Uses chosen" }).isVisible().catch(() => false))) {
      await card.getByLabel("Search uses").fill("office");
      await card.getByRole("button", { name: /^Add / }).first().click();
    }
  } else if (await file.count()) {
    await file.setInputFiles(fixture);
    await expect(card.getByRole("list", { name: "Files added" })).toBeVisible({ timeout: 60_000 });
  } else if (await radios.count()) {
    const question = (await card.getByRole("radiogroup").textContent()) ?? "";
    const pick = RADIO.find(([q]) => q.test(question))?.[1];
    if (pick) await card.getByRole("radio", { name: pick, exact: true }).check({ force: true });
    else await radios.first().check({ force: true });
  } else if (await checkboxes.count()) {
    await checkboxes.first().check({ force: true });
  } else if (await textarea.count()) {
    await textarea.first().fill("A short test description.");
  } else if (await text.count()) {
    const input = text.first();
    if ((await input.getAttribute("inputmode")) === "decimal") {
      const label = (await card.textContent()) ?? "";
      await input.fill(/percent/.test(label) ? "20" : /stories/.test(label) ? "2" : /angle/.test(label) ? "90" : "12");
    } else {
      await input.fill(/full name/.test((await card.textContent()) ?? "") ? "Test Applicant" : "Test answer");
    }
  }
  await page.getByRole("button", { name: "Next" }).click();
  await page.waitForTimeout(150);
  return true;
}

export async function answerEverything(page: Page, plan: Plan, fixture: string) {
  for (let i = 0; i < 200; i += 1) {
    if (!(await answerScreen(page, plan, fixture))) return;
  }
  throw new Error("the wizard did not reach review in 200 screens");
}

// On review: every field is filled or marked, and nothing is still to answer.
export async function expectReviewComplete(page: Page, title: string) {
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
  await axe(page, "review");
  await expect(page.getByText("Still to answer")).toHaveCount(0);
  await expect(page.getByText("Not answered yet")).toHaveCount(0);
}
