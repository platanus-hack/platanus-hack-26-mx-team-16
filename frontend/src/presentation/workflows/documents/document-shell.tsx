"use client";

import type { ReactNode } from "react";

interface DocumentShellProps {
  children: ReactNode;
}

export function DocumentShell({ children }: DocumentShellProps) {
  return (
    <div className="h-screen w-screen overflow-hidden bg-background">
      {children}
    </div>
  );
}
