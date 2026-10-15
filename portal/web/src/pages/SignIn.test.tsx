import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import * as api from "../api";
import SignIn from "./SignIn";

const renderPage = () => render(<MemoryRouter><SignIn /></MemoryRouter>);

describe("SignIn", () => {
  it("sends a link and tells the person to check their email", async () => {
    const spy = vi.spyOn(api, "requestLink").mockResolvedValue("sent");
    renderPage();
    await userEvent.type(screen.getByLabelText("Your email address"), "a@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Email me a sign-in link" }));
    expect(spy).toHaveBeenCalledWith("a@example.com");
    expect(await screen.findByText(/Check your email/)).toBeInTheDocument();
  });

  it("explains a rate limit in plain words", async () => {
    vi.spyOn(api, "requestLink").mockResolvedValue("too_many_requests");
    renderPage();
    await userEvent.type(screen.getByLabelText("Your email address"), "a@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Email me a sign-in link" }));
    expect(await screen.findByText(/asked for several links/)).toBeInTheDocument();
    expect(screen.getByText(/use the newest email/)).toBeInTheDocument();
  });

  it("explains a mail outage in plain words", async () => {
    vi.spyOn(api, "requestLink").mockResolvedValue("email_unavailable");
    renderPage();
    await userEvent.type(screen.getByLabelText("Your email address"), "a@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Email me a sign-in link" }));
    expect(await screen.findByText(/couldn't send the email/)).toBeInTheDocument();
  });
});
