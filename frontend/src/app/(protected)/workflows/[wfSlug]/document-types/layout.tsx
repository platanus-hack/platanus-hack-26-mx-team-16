import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Tipos de Documento",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
