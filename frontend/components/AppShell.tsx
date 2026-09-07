"use client";

import type { ReactNode } from "react";

type AppShellProps = {
  sidebar: ReactNode;
  children: ReactNode;
};

export default function AppShell({ sidebar, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">{sidebar}</aside>

      <main className="app-main">{children}</main>
    </div>
  );
}
