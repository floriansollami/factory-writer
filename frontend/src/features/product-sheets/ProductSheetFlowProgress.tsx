import { Check } from "lucide-react";

import type { ProductFlowStep } from "@/features/product-sheets/productSheetUtils";
import { cn } from "@/lib/utils";

type ProductSheetFlowProgressProps = {
  className?: string;
  currentStep: ProductFlowStep;
};

const steps: Array<{ id: ProductFlowStep; label: string }> = [
  { id: "product", label: "Produit" },
  { id: "sources", label: "Dossiers" },
  { id: "analysis", label: "Analyse" },
  { id: "context", label: "Contexte" },
  { id: "generation", label: "Génération" },
];

export function ProductSheetFlowProgress({
  className,
  currentStep,
}: ProductSheetFlowProgressProps) {
  const currentIndex = steps.findIndex((step) => step.id === currentStep);

  return (
    <div className={cn("grid gap-3", className)}>
      <div className="grid grid-cols-5 gap-2 max-md:grid-cols-1">
        {steps.map((step, index) => {
          const isDone = index < currentIndex;
          const isCurrent = index === currentIndex;

          return (
            <div
              key={step.id}
              className={cn(
                "rounded-2xl border border-[var(--color-stone)] bg-white/60 p-3",
                isDone && "border-[var(--color-sage-soft)] bg-[var(--color-sage-soft)]/55",
                isCurrent && "border-[var(--color-forest)] bg-white shadow-[0_12px_28px_rgba(23,49,36,0.1)]",
              )}
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "grid size-7 place-items-center rounded-full bg-[var(--color-surface-raised)] text-xs font-bold text-[var(--color-muted)]",
                    isDone && "bg-[var(--color-forest)] text-white",
                    isCurrent && "bg-[var(--color-gold-soft)] text-[var(--color-teak)]",
                  )}
                >
                  {isDone ? <Check className="size-4" /> : index + 1}
                </span>
                <span className="text-sm font-semibold text-[var(--color-ink)]">
                  {step.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

