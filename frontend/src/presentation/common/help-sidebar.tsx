"use client";

import { BookOpen, ExternalLink, MessageCircle, XIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/src/application/lib/utils";
import {
  Button,
  buttonVariants,
} from "@/src/presentation/components/ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetFooter,
} from "@/src/presentation/components/ui/sheet";

interface HelpSidebarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function HelpSidebar({ open, onOpenChange }: HelpSidebarProps) {
  const t = useTranslations("HelpSidebar");

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="!w-[90%] md:!w-2/3 lg:!w-1/3 !max-w-none"
        showCloseButton={false}
      >
        <div className="flex items-center gap-3 p-4 border-b">
          <SheetClose render={<Button variant="ghost" size="icon-sm" />}>
            <XIcon className="h-4 w-4" />
            <span className="sr-only">{t("close")}</span>
          </SheetClose>
          <h2 className="text-xl font-normal font-sans">{t("title")}</h2>
        </div>

        <div className="flex-1 py-6 px-4 overflow-y-auto">
          <div className="space-y-6">
            <section>
              <h3 className="text-lg font-medium mb-2">{t("howCanWeHelp")}</h3>
              <p className="text-muted-foreground">{t("exploreDescription")}</p>
            </section>

            <section>
              <h3 className="text-base font-medium mb-2">
                {t("usefulResources")}
              </h3>
              <ul className="space-y-2 text-muted-foreground">
                <li>• {t("quickStart")}</li>
                <li>• {t("tutorials")}</li>
                <li>• {t("faq")}</li>
                <li>• {t("demoVideos")}</li>
              </ul>
            </section>
          </div>
        </div>

        <SheetFooter className="border-t pt-4">
          <div className="flex flex-col gap-0 w-full">
            <a
              href="https://docs.llamit.ai"
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({ variant: "ghost" }),
                "justify-start gap-2 text-blue-400 hover:text-blue-500 hover:bg-blue-50"
              )}
            >
              <BookOpen className="h-4 w-4" />
              {t("readDocs")}
              <ExternalLink className="h-3 w-3 ml-auto" />
            </a>
            <a
              href="https://llamit.ai/contact"
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({ variant: "ghost" }),
                "justify-start gap-2 text-blue-400 hover:text-blue-500 hover:bg-blue-50"
              )}
            >
              <MessageCircle className="h-4 w-4" />
              {t("contactTeam")}
              <ExternalLink className="h-3 w-3 ml-auto" />
            </a>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
