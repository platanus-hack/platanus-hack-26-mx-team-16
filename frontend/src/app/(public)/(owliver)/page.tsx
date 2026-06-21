import type { Metadata } from "next";

import { ComoFuncionaView } from "@/src/presentation/owliver/marketing/como-funciona-view";

export const metadata: Metadata = {
  title: "Cómo funciona",
};

export default function ComoFuncionaPage() {
  return <ComoFuncionaView />;
}
