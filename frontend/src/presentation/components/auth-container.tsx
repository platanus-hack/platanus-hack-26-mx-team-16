import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { LocaleSwitcher } from "@/src/presentation/components/locale-switcher";

interface AuthContainerProps {
  icon: LucideIcon;
  title: string;
  description: string;
  children: ReactNode;
}

export function AuthContainer({
  icon: Icon,
  title,
  description,
  children,
}: AuthContainerProps) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[3fr_2fr] relative">
      <div className="absolute top-4 right-4 z-10">
        <LocaleSwitcher />
      </div>

      <div className="hidden lg:flex items-center justify-center bg-muted/30 p-12">
        <div className="max-w-md space-y-6 text-center">
          <div className="mx-auto h-48 w-48 rounded-full bg-muted/50 flex items-center justify-center">
            <div className="h-24 w-24 rounded-lg bg-muted/80" />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center p-8">
        <div className="w-full max-w-md space-y-8">
          <div className="space-y-4 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Icon className="h-6 w-6 text-primary" />
            </div>
            <div className="space-y-2">
              <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
              <p className="text-sm text-muted-foreground">{description}</p>
            </div>
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}
