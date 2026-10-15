import type { ReactNode } from "react";
import { Link } from "react-router";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-separator">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-semibold">Town of Newcastle · Permits</Link>
          <Link to="/my-applications" className="text-sm underline">My applications</Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8">{children}</main>
    </div>
  );
}
