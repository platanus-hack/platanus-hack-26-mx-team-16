import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Fuentes de Datos",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
