import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as layout from "../shell/useWideLayout";
import Messages from "./Messages";
import You from "./You";

const ME = { email: "a@example.com", role: "applicant", name: "Ada Lovelace", phone: "207-555-0100", mailing_address: "PO Box 1" };
const at = (path: string) => render(<MemoryRouter initialEntries={[path]}><Routes>
  <Route path="/you" element={<You />} />
  <Route path="/messages" element={<Messages />} />
  <Route path="/" element={<p>Home page</p>} />
</Routes></MemoryRouter>);

beforeEach(() => {
  vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
  vi.spyOn(api, "getMe").mockResolvedValue(ME);
});

describe("Messages", () => {
  it("is empty until the Town writes", async () => {
    at("/messages");
    expect(await screen.findByText("No messages yet. When the Town asks for something, or your application moves along, it shows here."))
      .toBeInTheDocument();
  });
});

describe("You", () => {
  it("shows the account's details; the email isn't editable", async () => {
    at("/you");
    expect(await screen.findByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("a@example.com")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Change/ })).toHaveLength(3); // name, phone, address
  });

  it("Change saves to the account", async () => {
    const put = vi.spyOn(api, "putMe").mockResolvedValue({ ...ME, phone: "207-555-0199" });
    at("/you");
    await userEvent.click(await screen.findByRole("button", { name: "Change phone" }));
    const box = screen.getByRole("textbox", { name: "Phone" });
    await userEvent.clear(box);
    await userEvent.type(box, "207-555-0199{Enter}");
    expect(put).toHaveBeenCalledWith({ name: "Ada Lovelace", phone: "207-555-0199", mailing_address: "PO Box 1" });
    expect(await screen.findByText("207-555-0199")).toBeInTheDocument();
  });

  it("signs out", async () => {
    const out = vi.spyOn(api, "signOut").mockResolvedValue();
    at("/you");
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(out).toHaveBeenCalled();
    await waitFor(() => expect(screen.getByText("Home page")).toBeInTheDocument());
  });
});
