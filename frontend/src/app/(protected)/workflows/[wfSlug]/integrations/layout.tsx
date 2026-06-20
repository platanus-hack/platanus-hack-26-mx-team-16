import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Integraciones del Workflow",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
