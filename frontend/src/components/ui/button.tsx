import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentPropsWithoutRef } from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-full text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "bg-[linear-gradient(135deg,var(--color-forest),var(--color-leaf))] px-5 py-2.5 text-white shadow-[0_18px_36px_rgba(23,49,36,0.18)] focus-visible:outline-[var(--color-forest)]",
        secondary:
          "bg-[var(--color-surface-raised)] px-5 py-2.5 text-[var(--color-forest)] hover:bg-[var(--color-sage-soft)]",
        ghost:
          "px-3 py-2 text-[var(--color-forest)] hover:bg-[var(--color-sage-soft)]",
      },
      size: {
        md: "h-11",
        sm: "h-9 px-4 text-xs",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

type ButtonProps = ComponentPropsWithoutRef<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  };

export function Button({ className, variant, size, asChild, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";

  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}
