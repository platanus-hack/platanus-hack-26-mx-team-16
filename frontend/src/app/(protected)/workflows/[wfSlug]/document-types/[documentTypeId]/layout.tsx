import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Tipo de Documento",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
