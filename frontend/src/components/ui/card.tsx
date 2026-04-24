import type { ComponentPropsWithoutRef } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: ComponentPropsWithoutRef<"section">) {
  return (
    <section
      className={cn(
        "rounded-[1.5rem] bg-[var(--color-surface-card)] p-5 shadow-[0_18px_44px_rgba(27,28,26,0.06)]",
        className,
      )}
      {...props}
    />
  );
}

export function CardTitle({ className, ...props }: ComponentPropsWithoutRef<"h2">) {
  return (
    <h2
      className={cn("font-serif text-xl font-semibold tracking-[-0.03em] text-[var(--color-ink)]", className)}
      {...props}
    />
  );
}
