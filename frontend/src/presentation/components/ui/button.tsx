"use client";

import { Button as ButtonPrimitive } from "@base-ui/react/button";

import { cn } from "@/src/application/lib/utils";
import {
  buttonVariants,
  type ButtonVariantProps,
} from "@/src/presentation/components/ui/button-variants";

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & ButtonVariantProps) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
