import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Acceso denegado",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
