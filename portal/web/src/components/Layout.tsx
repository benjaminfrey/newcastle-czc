import type { ReactNode } from "react";
import { Link, Outlet } from "react-router";

// The quiet toolbar and centred column for pages outside the application window.
export default function Layout({ children }: { children?: ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--app-ground)] text-[var(--app-label)]">
      <header className="border-b border-[var(--app-separator)] bg-[var(--app-row)]">
        <div className="mx-auto flex min-h-14 max-w-3xl items-center justify-between gap-4 px-4">
          <Link to="/" className="flex min-h-11 items-center gap-2.5 text-[17px] font-semibold no-underline">
            <img src="/town-seal.png" alt="" aria-hidden="true" className="size-7" width={28} height={28} />
            Town of Newcastle
          </Link>
          <Link to="/my-applications"
                className="flex min-h-11 items-center text-[17px] text-[var(--app-accent-text)] no-underline">
            My applications
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-6">{children ?? <Outlet />}</main>
    </div>
  );
}
