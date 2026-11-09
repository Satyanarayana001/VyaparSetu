import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../lib/auth";
import { I18nProvider } from "../lib/i18n";
import Login from "../pages/Login";

function setup() {
  return render(
    <QueryClientProvider client={new QueryClient()}><I18nProvider initial="en"><AuthProvider><MemoryRouter><Login /></MemoryRouter></AuthProvider></I18nProvider></QueryClientProvider>,
  );
}

describe("Login", () => {
  afterEach(() => vi.restoreAllMocks());

  it("disables sign-in until both fields are filled", async () => {
    const user = userEvent.setup();
    setup();
    const btn = screen.getByRole("button", { name: "Sign in" });
    expect(btn).toBeDisabled();
    await user.type(screen.getByLabelText("Email"), "a@b.test");
    await user.type(screen.getByLabelText("Password"), "x");
    expect(btn).toBeEnabled();
  });

  it("shows the server's error message on a failed sign-in", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: { code: "INVALID_CREDENTIALS", message: "Email or password is incorrect." } }), { status: 401 }));
    const user = userEvent.setup();
    setup();
    await user.type(screen.getByLabelText("Email"), "a@b.test");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
  });

  it("shows a clear message when the server can't be reached", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fail"));
    const user = userEvent.setup();
    setup();
    await user.type(screen.getByLabelText("Email"), "a@b.test");
    await user.type(screen.getByLabelText("Password"), "x");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/Can't reach the server/));
  });
});
