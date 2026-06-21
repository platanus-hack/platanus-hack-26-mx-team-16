import type { Metadata } from "next";

import { ComoFuncionaView } from "@/src/presentation/owliver/marketing/como-funciona-view";

export const metadata: Metadata = {
  title: "Owliver — Audita tu web y tu IA. Recibe un grado A–F.",
  description:
    "Un equipo de agentes de IA audita tu sitio (OWASP web + superficie agéntica: chatbots y widgets de IA) y te entrega un grado A–F con evidencia, en menos de 90 segundos. Precios por créditos.",
};

export default function ComoFuncionaPage() {
  return <ComoFuncionaView />;
}
