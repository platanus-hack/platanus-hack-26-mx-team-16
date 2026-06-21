import type { Metadata } from "next";

import { OnboardingView } from "@/src/presentation/owliver/onboarding/onboarding-view";

export const metadata: Metadata = {
  title: "Primeros pasos",
};

export default function OnboardingPage() {
  return <OnboardingView />;
}
