/**
 * ScanFormDialog (§F5) — mounts <ScanForm> inside a Dialog so `/` (leaderboard)
 * can open the scan form as a modal without a route change. Controlled by the
 * caller (open / onOpenChange). On a successful create the form already
 * router.push()es to /scans/[id]; we also close the dialog via onSuccess.
 */
"use client";

import { useState } from "react";

import {
  Dialog,
  DialogBody,
  DialogHeader,
  DialogPopup,
  DialogTitle,
  DialogTrigger,
} from "@/src/presentation/components/ui/dialog";
import { ScanForm } from "@/src/presentation/owliver/scan/scan-form";

export type ScanFormDialogProps = {
  /**
   * Trigger element (e.g. the violet "Audita cualquier URL →" span styled with
   * buttonVariants). Passed straight to Base UI's `render` so the trigger IS
   * this element — no nested interactive wrapper.
   */
  children: React.ReactElement;
};

export function ScanFormDialog({ children }: ScanFormDialogProps) {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={children} />
      <DialogPopup className="max-w-xl p-6">
        <DialogHeader>
          <DialogTitle>Auditar un sitio</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <ScanForm onSuccess={() => setOpen(false)} />
        </DialogBody>
      </DialogPopup>
    </Dialog>
  );
}
