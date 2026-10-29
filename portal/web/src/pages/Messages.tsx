import AppShell from "../shell/AppShell";

// Messages (projects brief §3.6): empty until Milestone 6 puts the Town's requests and a project's
// status changes here.
export default function Messages() {
  return (
    <AppShell title="Messages">
      <div className="mx-auto flex max-w-lg flex-col gap-3 px-4 py-6">
        <h2 className="text-[30px] font-bold leading-tight">Messages</h2>
        <p className="max-w-[46ch] text-[15px] text-[var(--app-secondary-label)]">
          No messages yet. When the Town asks for something, or your application moves along, it shows here.
        </p>
      </div>
    </AppShell>
  );
}
