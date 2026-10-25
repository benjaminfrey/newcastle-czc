import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import App from "../App";
import { peekPendingStart } from "../pendingStart";
import { saveProperty } from "../property";
import { saveAnswers } from "../screener";
import * as layout from "../shell/useWideLayout";
import SignInForm from "../components/SignInForm";

vi.mock("../components/ParcelMap", () => ({ default: () => <div>map</div> }));

const OUTCOME: api.Outcome = {
  application: "small_project_plan", code_name: "Small Project Plan", plain: "For building work.", reviewer: "Code Enforcement Officer",
  certainty: "needed", district: "D1", district_name: "Rural (D1)", in_portal: true, days: [],
  why: { cite: "8.10.b.1", text: "All new buildings…", ruling: null },
};

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
  saveAnswers({ project: ["build"], use_key: null,
    building: { kind: "new", gross_floor_area_sf: 1200, total_floor_area_sf: null, parking_spaces: null, new_dwelling_units: null, homes_added_last_5_years: null },
    division: { lots_after: null, divided_last_5_years: null } });
  saveProperty({ source: "lookup", parcel_id: 229, map_lot: "004-036", district_code: "D1", district_codes: ["D1"],
                 on_state_highway: false, disputed: false, note: "", as_of: "2026-10-15" });
  vi.spyOn(api, "runScreener").mockResolvedValue({ outcomes: [OUTCOME], notes: [], not_listed: [], town_only: false, drafts_used: [] });
});

const at = (path: string) => {
  window.history.pushState({}, "", path);
  return render(<App />);
};

describe("the start window", () => {
  it("sits in a card headed by its step, with Home above", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    at("/start/needs");
    expect(await screen.findByText("What you'll need")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
    expect(screen.queryByRole("navigation", { name: "Steps" })).not.toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 2, name: /^You'll need a Small Project Plan/ })).toHaveClass("text-[20px]");
  });

  it("Start this application goes to the sign-in screen when signed out", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    at("/start/needs");
    await userEvent.click(await screen.findByRole("button", { name: "Start this application: Small Project Plan" }));
    expect(await screen.findByRole("heading", { name: "Sign in to apply" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(window.location.pathname).toBe("/start/signin");
    expect(peekPendingStart()?.formKey).toBe("small_project_plan");
  });

  it("old addresses lead to the new steps", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    at("/start/results");
    expect(await screen.findByRole("heading", { level: 2, name: /^You'll need a Small Project Plan/ })).toBeInTheDocument();
  });
});

describe("SignInForm", () => {
  it("its button is the near-black filled one", () => {
    render(<MemoryRouter><SignInForm /></MemoryRouter>);
    expect(screen.getByRole("button", { name: "Email me a sign-in link" })).toHaveClass("btn-filled");
  });

  it("shows Check your email with the address and the expiry, and sends again", async () => {
    const spy = vi.spyOn(api, "requestLink").mockResolvedValue("sent");
    render(<MemoryRouter><SignInForm /></MemoryRouter>);
    await userEvent.type(screen.getByLabelText("Your email address"), "a@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Email me a sign-in link" }));
    expect(await screen.findByText("Check your email")).toBeInTheDocument();
    expect(screen.getByText(/a@example\.com/)).toBeInTheDocument();
    expect(screen.getByText(/works once, for 15 minutes/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Send it again" }));
    expect(spy).toHaveBeenCalledTimes(2);
  });
});

describe("Home", () => {
  it("one primary action", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    at("/");
    const start = await screen.findByRole("link", { name: "Find out what you need" });
    expect(start).toHaveAttribute("href", "/start");
    expect(screen.getByRole("img", { name: "Town of Newcastle seal" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Continue an application" })).not.toBeInTheDocument();
  });

  it("offers to continue when signed in", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    at("/");
    expect(await screen.findByRole("link", { name: "Continue an application" })).toHaveAttribute("href", "/my-applications");
  });
});
