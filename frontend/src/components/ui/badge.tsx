import type { ComponentPropsWithoutRef } from "react";

import { cn } from "@/lib/utils";

type BadgeTone = "success" | "warning" | "neutral" | "danger";

const toneClass: Record<BadgeTone, string> = {
  success: "bg-[var(--color-sage-soft)] text-[var(--color-forest)]",
  warning: "bg-[var(--color-gold-soft)] text-[var(--color-teak)]",
  neutral: "bg-[var(--color-stone)] text-[var(--color-muted)]",
  danger: "bg-[var(--color-error-soft)] text-[var(--color-error)]",
};

type BadgeProps = ComponentPropsWithoutRef<"span"> & {
  tone?: BadgeTone;
};

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.12em]",
        toneClass[tone],
        className,
      )}
      {...props}
    />
  );
}
