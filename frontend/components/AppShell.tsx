"use client";

import { useEffect, type ReactNode } from "react";

type AppShellProps = {
  sidebar: ReactNode;
  children: ReactNode;
  mobileOpen: boolean;
  onMobileOpenChange: (open: boolean) => void;
};

export default function AppShell({
  sidebar,
  children,
  mobileOpen,
  onMobileOpenChange,
}: AppShellProps) {

  useEffect(() => {
    if (!mobileOpen) return;

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onMobileOpenChange(false);
      }
    }

    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, [mobileOpen, onMobileOpenChange]);

  return (
    <div className="app-shell">
      <div className="mobile-toolbar">
        <button
          type="button"
          className="mobile-documents-button"
          onClick={() => onMobileOpenChange(true)}
          aria-expanded={mobileOpen}
          aria-controls="document-sidebar"
        >
          ☰ Documents
        </button>
        <span>DocMind</span>
      </div>

      {mobileOpen && (
        <button
          type="button"
          className="mobile-sidebar-backdrop"
          aria-label="Close documents panel"
          onClick={() => onMobileOpenChange(false)}
        />
      )}

      <aside
        id="document-sidebar"
        className={`app-sidebar ${mobileOpen ? "app-sidebar--open" : ""}`}
      >
        {sidebar}
      </aside>

      {mobileOpen && (
        <button
          type="button"
          className="mobile-sidebar-close"
          aria-label="Close documents panel"
          onClick={() => onMobileOpenChange(false)}
        >
          ✕
        </button>
      )}

      <main className="app-main">{children}</main>
    </div>
  );
}