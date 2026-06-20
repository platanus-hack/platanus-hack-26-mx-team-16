import {
  Input as InputPrimitive,
  type InputProps,
} from "@base-ui/react/input";
import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";

import { cn } from "@/src/application/lib/utils";

const inputVariants = cva(
  "dark:bg-input/30 border-input focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:aria-invalid:border-destructive/50 rounded-md border bg-white px-2.5 py-1 text-base shadow-xs transition-[color,box-shadow] file:text-sm file:font-medium focus-visible:ring-[3px] aria-invalid:ring-[3px] md:text-sm file:text-foreground placeholder:text-muted-foreground w-full min-w-0 outline-none file:inline-flex file:border-0 file:bg-transparent disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      size: {
        default: "h-9 file:h-7",
        lg: "h-10 file:h-8",
        xl: "h-11 file:h-9",
      },
    },
    defaultVariants: {
      size: "default",
    },
  }
);

type InputComponentProps = React.ComponentProps<"input"> &
  VariantProps<typeof inputVariants> & {
    /**
     * Base UI's controlled-value callback. Base UI's `Field.Control`
     * intercepts the native `onChange` to wire validation state, so any
     * userland `onChange` handler is silently dropped — controlled
     * forms MUST use `onValueChange` instead.
     */
    onValueChange?: InputProps["onValueChange"];
  };

function Input({
  className,
  type,
  size,
  ...props
}: InputComponentProps) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(inputVariants({ size, className }))}
      {...props}
    />
  );
}

export { Input, inputVariants };
