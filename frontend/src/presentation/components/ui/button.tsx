"use client";

import { Button as ButtonPrimitive } from "@base-ui/react/button";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/src/application/lib/utils";

const buttonVariants = cva(
  // M3 Expressive: pill shape, state-layer overlay (before: uses current/on-color), emphasized easing + press.
  "relative isolate inline-flex shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-full border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap select-none outline-none transition-[color,background-color,box-shadow,transform] duration-150 ease-[cubic-bezier(0.2,0,0,1)] group/button focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:border-destructive aria-invalid:ring-destructive/20 aria-invalid:ring-[3px] disabled:pointer-events-none disabled:opacity-50 active:scale-[0.97] [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 before:pointer-events-none before:absolute before:inset-0 before:rounded-[inherit] before:bg-current before:opacity-0 before:transition-opacity hover:before:opacity-[0.08] active:before:opacity-[0.12]",
  {
    variants: {
      variant: {
        // Filled
        default: "bg-primary text-primary-foreground shadow-xs",
        // Filled tertiary ("owl-eyes" amber CTA)
        tertiary: "bg-tertiary text-on-tertiary shadow-xs",
        // Tonal
        secondary: "bg-secondary text-secondary-foreground",
        tonal: "bg-secondary text-secondary-foreground",
        // Elevated
        elevated: "bg-card text-primary shadow-sm",
        // Outlined
        outline:
          "border-outline bg-transparent text-primary aria-expanded:bg-accent aria-expanded:text-accent-foreground",
        // Text
        ghost: "text-primary aria-expanded:bg-accent aria-expanded:text-accent-foreground",
        destructive: "bg-destructive/15 text-destructive-deep",
        success: "bg-success text-success-foreground shadow-xs",
        link: "text-primary underline-offset-4 before:hidden hover:underline",
      },
      size: {
        default: "h-10 gap-1.5 px-5",
        xs: "h-7 gap-1 px-3 text-xs [&_svg:not([class*='size-'])]:size-3",
        sm: "h-9 gap-1 px-4",
        lg: "h-11 gap-1.5 px-6",
        xl: "h-12 gap-2 px-7 text-base",
        icon: "size-10",
        "icon-xs": "size-7 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-9",
        "icon-lg": "size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
