"use client";

import type { ComponentProps, ReactNode } from "react";

import { Button } from "@/src/presentation/components/ui/button";
import { Spinner } from "@/src/presentation/components/ui/spinner";

type ButtonProps = ComponentProps<typeof Button>;

interface ActionButtonProps extends ButtonProps {
  /**
   * Icon rendered before the label (e.g. a Lucide `<FileUp />`).
   * Swapped for a spinner while `loading` is true.
   */
  icon?: ReactNode;
  /** Shows a spinner in place of the icon and disables the button. */
  loading?: boolean;
}

/**
 * Button with a built-in loading state: while `loading`, the `icon` is
 * swapped for a spinner and the button is disabled. The spinner inherits
 * the button's text color (`currentColor`), so it stays visible on any
 * variant. The label is passed as `children`.
 */
export function ActionButton({
  icon,
  loading = false,
  disabled,
  size = "default",
  children,
  ...props
}: ActionButtonProps) {
  const spinnerSize =
    size === "xs" || size === "sm" || (typeof size === "string" && size.startsWith("icon"))
      ? "xs"
      : "sm";

  return (
    <Button size={size} disabled={disabled || loading} {...props}>
      {loading ? (
        <Spinner size={spinnerSize} className="border-current/30 border-t-current" />
      ) : (
        icon
      )}
      {children}
    </Button>
  );
}
